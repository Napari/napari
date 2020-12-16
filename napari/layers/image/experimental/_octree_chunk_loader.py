"""OctreeChunkLoader class.

Uses ChunkLoader to load data into OctreeChunks in the octree.
"""
import logging
from concurrent.futures import Future
from typing import Dict, List, Set

from ....components.experimental.chunk import LayerRef, chunk_loader
from .octree import Octree
from .octree_chunk import OctreeChunk, OctreeChunkKey, OctreeLocation

LOGGER = logging.getLogger("napari.octree.loader")

# TODO_OCTREE make this a config. This is how many levels "up" we look
# for tiles to draw at levels above the ideal how. These tiles give
# us lots of coverage quickly, so we load and draw then even before
# the ideal level
NUM_ANCESTORS_LEVELS = 3


class OctreeChunkLoader:
    """Load data into OctreeChunks in the octree.

    The loader is given draw_set, the chunks we are currently drawing, and
    ideal_chunks, the chunks which are in view at the desired level of the
    octree.

    The ideal level was chosen because its image pixels best match the
    screen pixels. Using higher resolution than that is okay, but it's
    wasting memory. Using lower resolution is better than nothing, but it's
    going to be blurrier than the ideal level.

    Our get_drawable_chunks() method iterates through the ideal_chunks
    choosing what chunks to load, in what order, and producing the set of
    chunks the visual should draw.

    Choosing what chunks to load and draw is the heart of octree rendering.
    We use the tree structure to find child or parent chunks, or chunks
    futher up the tree: ancestor chunks.

    The goal is to pretty quickly load all the ideal chunks, since that's
    what we really want to draw. But in the meantime we load and display
    chunks at lower or high resolutions. In some cases because they already
    loaded and even already being drawn. In other cases though we load
    chunk from high level because they provide "coverage" quickly.

    As you go up to higher levels from the ideal level, the chunks on those
    levels cover more and more chunks on the ideal level. As you go up
    levels they cover this number of ideal chunks: 4, 9, 16, 25.

    The data from higher levels is blurry compared to the ideal level, but
    getting something "reasonable" on the screen quickly often leads to the
    best user experience. For example, even "blurry" data is often good
    enough for them to keep navigating, to keep panning and zooming looking
    for whatever they are looking for.

    Parameters
    ----------
    octree : Octree
        The octree we are loading chunks for, and that we are drawing.
    layer_ref : LayerRef
        A weak reference to the layer we are loading chunks for.

    Attributes
    ----------
    _futures : Future
        Futures for chunks which are loading or queued for loading.
    _last_drawable : Set[OctreeLocation]
        What did draw last frame. Only for logging, so we don't spam the log.
    """

    def __init__(self, octree: Octree, layer_ref: LayerRef):
        self._octree = octree
        self._layer_ref = layer_ref

        self._futures: Dict[OctreeLocation, Future] = {}
        self._last_drawable: Set[OctreeLocation] = set()

    def get_drawable_chunks(
        self, drawn_set: Set[OctreeChunkKey], ideal_chunks: List[OctreeChunk],
    ) -> List[OctreeChunk]:
        """Return the chunks that should be drawn.

        The ideal chunks are within the bounds of the OctreeView, but those
        chunks may or may not be in memory. We only return chunks which
        are in memory.

        Generally we want to draw the "best available" data. Howevever that
        data might not be at the ideal level. Sometimes we even load chunks
        at a higher level before loading the ideal chunks. To get
        "coverage" quickly.

        So we look in two directions:
        1) Up, to find a chunk at a higher (coarser) level.
        2) Down, to look for a drawable chunk at a lower (finer) level.

        The TiledImageVisual can draw overlapping tiles/chunks. For example
        suppose below B and C are ideal chunks, but B is drawable while C
        is not. We search up from C and find A.

        ----------
        |    A   |
        | --- ---|
        |  B | C |
        |---------

        TiledImageVisual will render A first, because it's at a higher
        level, and then B. So the visual will render B and A with B on top.
        The region defined by C is showing A, until C is ready to draw.

        Parameters
        ----------
        drawn_chunk_set : Set[OctreeChunkKey]
            The chunks which the visual is currently drawing.
        ideal_chunks : List[OctreeChunk]
            The chunks which are visible to the current view.

        Return
        ------
        List[OctreeChunk]
            The chunks that should be drawn.
        """
        LOGGER.debug(
            "get_drawable_chunks: draw_set=%d ideal_chunks=%d",
            len(drawn_set),
            len(ideal_chunks),
        )

        # Build up the chunks we want to draw. Used a dict instead of a
        # set so it's ordered. The values are just 1.
        drawable = {}

        # Permanent chunks are ones we always want to draw no matter where
        # the view is. For now this is just the root tile. These get loaded
        # first which is what we want.
        permanent = self._get_permanent_chunks()
        self._load_and_add(drawable, permanent)

        # Now get coverage for every ideal chunk. This might include
        # the ideal chunk itself and/or chunks from other levels.
        for ideal_chunk in ideal_chunks:
            coverage = self._get_coverage(ideal_chunk, drawn_set)
            self._load_and_add(drawable, coverage)

        # Log all drawables.
        self._log_drawables(drawable)

        # Cancel all futures (in progress loads) that are no longer
        # drawable chunks. When panning or zooming quickly we create and
        # cancel a *lot* of futures. Which is fine, it's pretty fast, and
        # we very much want to avoid loading chunks that we no long need.
        self._cancel_futures(drawable)

        # Note the ones we drew, only for logging purposes.
        self._last_drawable = drawable

        # Kick off loads for every ideal chunk last.
        for ideal_chunk in ideal_chunks:

            # Load might be sync or async. If it was sync we can use the
            # chunk this frame. Otherwise we have to wait until
            # OctreeImage.on_chunk_loaded() is called some time later.
            if ideal_chunk.needs_load:
                if self._load_chunk(ideal_chunk):
                    drawable.append(ideal_chunk)

        # Return them all.
        return list(drawable)

    def _load_and_add(
        self, drawable: Dict[OctreeChunk, int], chunks: List[OctreeChunk]
    ):
        """Load chunks if needed and add in-memory chunks to the drawable dict.

        Parameters
        ----------
        drawable : Dict[OctdreeChunk, int]
            The chunks we are planning to draw.
        chunks : List[OctreeChunks]
            The chunks to and add to the drawable dict.

        Return
        ------
        List[OctreeChunks]
            Chunks that in memory and can be drawn.
        """
        memory = self._load_if_needed(chunks)
        for chunk in memory:
            drawable[chunk] = 1
        LOGGER.debug("Added %d chunks", len(memory))

    def _load_if_needed(self, chunks: List[OctreeChunk]) -> List[OctreeChunk]:
        """Load every chunk that needs it, and return the ones in memory.

        Parameters
        ----------
        chunks : List[OctreeChunk]
            The chunks to load and return if in memory.

        Returns
        -------
        List[OctreeChunks]
            The chunk that are in memory.
        """
        memory = []
        for chunk in chunks:
            if chunk.in_memory:
                memory.append(chunk)  # Already in memory.
            if chunk.needs_load:
                if self._load_chunk(chunk):  # Initiate a load.
                    memory.append(chunk)  # It was loaded synchronously
        return memory

    def _log_drawables(self, drawable: Set[OctreeChunk]) -> None:
        """Log the locations in the drawable set.

        Parameters
        ----------
        drawable : Set[OctreeChunk]
            The chunks we are going to draw.
        """
        if not self._drawables_changed(drawable):
            return  # Don't spam the log with the same thing over and over.

        LOGGER.debug(
            "Found drawable=%d futures=%d", len(drawable), len(self._futures),
        )

        for octree_chunk in drawable:
            LOGGER.debug("Drawable at %s", octree_chunk.location)

    def _drawables_changed(self, drawable: Set[OctreeChunk]) -> bool:
        """Return True if the locations we are drawing changed.

        Parameters
        ----------
        drawable : Set[OctreeChunk]
            The chunks we are going to draw.

        Return
        ------
        bool
            True if the locations we are drawing changed.
        """
        # If different sizes there was definitively a change!
        if len(drawable) != len(self._last_drawable):
            return True

        # Return True only if there was a change in the set.
        return drawable != self._last_drawable

    def _get_permanent_chunks(self) -> List[OctreeChunk]:
        """Get any permanent chunks we want to always draw.

        Right now it's just the root tile. We draw this so that we always
        have at least some minimal coverage when the camera moves to a new
        place. On a big enough dataset though when zoomed in we might be
        "inside" a single pixel of the root tile. So it's just providing a
        background color at that point.

        Return
        ------
        List[OctreeChunk]
            Any extra chunks we should draw.
        """
        # We say create=True because the root is not part of the current
        # intersection. However since it's permanent once created and
        # loaded it should always be available. As long as we don't garbage
        # collect it!
        root_tile = self._octree.levels[-1].get_chunk(0, 0, create=True)
        return [root_tile]

    def _get_coverage(
        self, ideal_chunk: OctreeChunk, drawn_set: Set[OctreeChunkKey]
    ) -> List[OctreeChunk]:
        """Return the chunks to draw for this one ideal chunk.

        If the ideal chunk is already being drawn, we just return it.
        Nothing else needs to be drawn. Otherwise we look up down the tree
        to find what chunks we can to draw to "cover" this chunk.

        Note that drawn_chunk_set might be smaller than what
        get_drawable_chunks has been returning, because it only contains
        chunks that actually got drawn to the screen.

        We return drawable chunks to the visual, but the visual might take
        some number of frames to get them all on the screen. This is
        because it takes time to move a chunk's data into VRAM, so the
        visual tends to only draw so many new chunks per frame. Right
        now in fact it only draws one new chunk per frame.

        So if we return the same 40 in-memory chunks from our
        get_drawable_chunks() every frame, it might be 40 frames until they
        are all actually drawn on the screen.

        For this reason we return multiple chunks for an ideal chunk even
        if the ideal chunk itself is in memory. Once the ideal chunk is in
        the draw_set though, can return just the ideal chunk alone.

        Parameters
        ----------
        ideal_chunk : OctreeChunk
            The ideal chunk we'd like to draw.
        drawn_chunk_set : Set[OctreeChunkKey]
            The chunks which the visual is currently drawing.

        Return
        ------
        List[OctreeChunk]
            The chunks that should be drawn to cover this one ideal chunk.
        """

        # If the ideal chunk is already being drawn, that's all we need,
        # there is no point in returning more than that.
        if ideal_chunk.in_memory and ideal_chunk.key in drawn_set:
            LOGGER.debug(
                "_get_coverage: Return only ideal %s", ideal_chunk.location
            )
            return [ideal_chunk]

        # Get alternates for this chunk, from other levels.
        family = self._get_family(ideal_chunk)

        ideal_level_index = ideal_chunk.location.level_index

        # For levels below the ideal level, we only keep an alternate if
        # it's already being drawn. This is usually when zooming out. The
        # alternates are "too small" but still look fine on screen.
        #
        # For levels above the ideal level, we will load and draw them. We
        # even sort so they get loaded and drawn *before* the ideal chunk.
        #
        # We do this because they provide coverage very quickly, and the
        # best user experience is to see imagery quickly even if not at the
        # ideal level.
        def keep_chunk(chunk) -> bool:
            lower = chunk.location.level_index < ideal_level_index

            if lower:
                return chunk.key in drawn_set

            return True

        keep = [chunk for chunk in family if keep_chunk(chunk)]

        LOGGER.debug(
            "_get_coverage: Keeping %d of %d for %s",
            len(keep),
            len(family),
            ideal_chunk.location,
        )

        # Put ideal one at the end so it loads last.
        if ideal_chunk.in_memory:
            keep.append(ideal_chunk)

        return keep

    def _get_family(self, ideal_chunk: OctreeChunk) -> List[OctreeChunk]:
        """Return chunks below and above this ideal chunk.

        Parameters
        ----------
        ideal_chunk : OctreeChunk
            Get children and parents of this chunk.

        Return
        ------
        List[OctreeNode]
            Parents and children we should load and/or draw.
        """
        # Get any direct children which are in memory. Do not create
        # OctreeChunks or use children that are not already in memory.
        children = self._octree.get_children(
            ideal_chunk, create=False, in_memory=True
        )

        # Get the parent and maybe more distant ancestors. Even if we have
        # all four children, we still consider loading and drawing these
        # because they will provide more coverage. They will cover the
        # ideal chunk plus more.
        ancestors = self._octree.get_ancestors(
            ideal_chunk, NUM_ANCESTORS_LEVELS
        )

        return children + ancestors

    def _load_chunk(self, octree_chunk: OctreeChunk) -> None:
        """Load the data for one OctreeChunk.

        Parameters
        ----------
        octree_chunk : OctreeChunk
            Load the data for this chunk.
        """
        # We only want to load a chunk if it's not already in memory, if a
        # load was not started on it.
        assert not octree_chunk.in_memory
        assert not octree_chunk.loading

        LOGGER.debug("_load_chunk: %s", octree_chunk.location)

        # Create a key that points to this specific location in the octree.
        layer_key = self._layer_ref.layer_key
        key = OctreeChunkKey(layer_key, octree_chunk.location)

        # The ChunkLoader takes a dict of chunks that should be loaded at
        # the same time. Today we only ever ask it to a load a single chunk
        # at a time. In the future we might want to load multiple layers at
        # once, so they are in sync, or load multiple locations to bundle
        # things up for efficiency.
        chunks = {'data': octree_chunk.data}

        # Mark that this chunk is being loaded.
        octree_chunk.loading = True

        # Create the ChunkRequest and load it with the ChunkLoader.
        request = chunk_loader.create_request(self._layer_ref, key, chunks)
        satisfied_request, future = chunk_loader.load_chunk(request)

        if satisfied_request is not None:
            # The load was synchronous. Some situations were the
            # ChunkLoader loads synchronously:
            #
            # 1) The force_synchronous config option is set.
            # 2) The data already was an ndarray, there's nothing to "load".
            # 3) The data is Dask or similar, but based on past loads it's
            #    loading so quickly that we decided to load it synchronously.
            # 4) The data is Dask or similar, but we already loaded this
            #    exact chunk before, so it was in the cache.
            #

            # Whatever the reason, the data is now ready to draw.
            octree_chunk.data = satisfied_request.chunks.get('data')
            assert octree_chunk.in_memory

            # The chunk as been loaded. It can be a drawable chunk that we
            # return to the visual.
            return True

        # An async load was initiated. The load will probably happen in a
        # worker thread. When the load completes QtChunkReceiver will call
        # OctreeImage.on_chunk_loaded() with the data.

        # We save the future in case we need to cancel it if the camera
        # move such that the chunk is no longer needed. We can only cancel
        # the future if the worker thread as not started loading it.
        assert future
        LOGGER.debug("Saving future %s", octree_chunk.location)
        self._futures[octree_chunk.location] = future

        return False

    def _cancel_futures(self, drawable: Set[OctreeLocation]) -> None:
        """Cancel futures not in the drawable_set.

        Any futures not in the drawable set are stale. There is no point in
        loading them. So we cancel them if we can. If a worker has already
        started on the load we can't cancel it. But that chunk will be
        ignored when it does load.

        Parameters
        ----------
        drawable : Set[OctreeLocations]
            The set of locations we are asking the visual to draw.
        """
        before = len(self._futures)

        # Iterate through every future.
        for location, future in list(self._futures.items()):
            # If it's not in the drawable set then cancel it.
            if location not in drawable:
                # Future.cancel() will return False if a worker has already
                # starated on the load.
                success = future.cancel()

                LOGGER.debug(
                    "Cancel future %sfor %s",
                    "" if success else "failed ",
                    location,
                )

                try:
                    del self._futures[location]
                except KeyError:
                    # Our self.on_chunk_loaded might have been called even
                    # while we were iterating! In which case the future
                    # might no longer exist. Log for now, but not an error.
                    LOGGER.debug(
                        "_cancel_futures: Missing Future %s", location
                    )
            else:
                LOGGER.debug("Keeping: %s", location)

        kept = len(self._futures)
        cancelled = before - kept
        if before > 0 or kept > 0:
            LOGGER.debug(
                "Futures: before=%d cancelled=%d kept=%d",
                before,
                cancelled,
                kept,
            )

    def on_chunk_loaded(self, octree_chunk: OctreeChunk) -> None:
        """The given OctreeChunk was loaded.

        We just clear out our future which is no longer relevant.

        Parameters
        ----------
        octree_chunk : OctreeChunk
            The octree chunk that was loaded.
        """
        location = octree_chunk.location
        try:
            del self._futures[location]
        except KeyError:
            # This can happen if the location went out of view and the
            # future was deleted in self._cancel_futures. Log for now
            # but it's really not an error at all.
            LOGGER.debug("on_chunk_loaded: Missing Future %s", location)
