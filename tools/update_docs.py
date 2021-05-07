from pathlib import Path

from qtpy.QtCore import QTimer
from qtpy.QtWidgets import QApplication

from napari._qt.dialogs.preferences_dialog import PreferencesDialog
from napari._qt.qt_resources import get_stylesheet
from napari.utils.settings._defaults import CORE_SETTINGS

REPO_ROOT_PATH = Path(__file__).resolve().parents[1]
GUIDES_PATH = REPO_ROOT_PATH / "docs" / "guides"
IMAGES_PATH = GUIDES_PATH / "images"


def generate_images():
    """"""
    app = QApplication([])
    pref = PreferencesDialog()
    pref.setStyleSheet(get_stylesheet("dark"))

    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(pref.close)
    timer.start(2000)

    pref.show()

    for idx, setting in enumerate(CORE_SETTINGS):
        title = getattr(setting.Config, "title").lower()
        pref.set_current_index(idx)
        pixmap = pref.grab()
        pixmap.save(str(IMAGES_PATH / f"preferences-{title}.png"))

    def grab():
        pixmap = pref._reset_dialog.grab()
        pixmap.save(str(IMAGES_PATH / "preferences-reset.png"))
        pref._reset_dialog.close()

    timer2 = QTimer()
    timer2.setSingleShot(True)
    timer2.timeout.connect(grab)
    timer2.start(300)

    pref.restore_defaults()

    app.exec_()


TEMPLATE_START = """(preferences)=

# Preferences

Starting with version 0.4.7, napari codebase include internationalization
(i18n) and now offers the possibility of installing language packs, which
provide localization (l10n) enabling the user interface to be displayed in
different languages.

## Sections
"""

TEMPLATE_SECTION = """
### {title}

{description}

![{section}](images/preferences-{section}.png)
"""

TEMPLATE_FIELD = """- **{title}** *({field})*: {description} (Default: `{default}`).
"""

TEMPLATE_END = """
## Reset to defaults

### Using the UI

Click on the `Restore defaults` button.

![{reset}](images/preferences-reset.png)

### Using the CLI

```bash
napari --reset
```

## Changing settings programmatically

```python
from napari.utils.settings import SETTINGS

SETTINGS.appearance.theme = "light"
```

"""


def create_preferences_docs():
    """"""
    text = TEMPLATE_START
    for setting in CORE_SETTINGS:
        title = getattr(setting.Config, "title")
        description = setting.__doc__

        text += TEMPLATE_SECTION.format(
            section=title.lower(), title=title, description=description
        )
        _preferences_exclude = getattr(
            setting.NapariConfig, "preferences_exclude", []
        )
        preferences_managed = getattr(
            setting.NapariConfig, "preferences_managed", []
        )
        # schema = setting.schema()

        schema = setting.__fields__
        for field in sorted(setting.__fields__):
            if field not in preferences_managed:
                data = schema[field].field_info
                # print(dir(schema[field]))
                default = repr(schema[field].get_default())
                title = data.title
                description = data.description
                try:
                    ty = schema[field].type_
                    print(ty)
                    print(ty.choices())
                except Exception:
                    pass
                # print(field, title, description, default)
                # print(data)
                text += TEMPLATE_FIELD.format(
                    field=field,
                    title=title,
                    description=description,
                    default=default,
                )

    text += TEMPLATE_END

    with open(GUIDES_PATH / "preferences.md", "w") as fh:
        fh.write(text)


if __name__ == "__main__":
    generate_images()
    create_preferences_docs()
