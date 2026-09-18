"""Compose the responsive Home Assistant dashboard from its device cards."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HA_DIR = ROOT / "homeassistant"


def indent(text: str, spaces: int) -> str:
    prefix = " " * spaces
    return "\n".join(prefix + line if line else "" for line in text.splitlines())


def conditional_card(media_query: str, card: str) -> str:
    return (
        "  - type: conditional\n"
        "    conditions:\n"
        "      - condition: screen\n"
        f'        media_query: "{media_query}"\n'
        "    card:\n"
        f"{indent(card, 6)}"
    )


def as_list_item(mapping: str) -> str:
    """Convert a top-level YAML mapping into one list item."""
    lines = mapping.splitlines()
    lines[0] = "- " + lines[0]
    return "\n".join([lines[0], *("  " + line if line else "" for line in lines[1:])])


def main() -> None:
    desktop = (HA_DIR / "comfortzone-desktop-card.yaml").read_text(encoding="utf-8-sig").strip()
    tablet = (HA_DIR / "comfortzone-tablet-card.yaml").read_text(encoding="utf-8-sig").strip()
    mobile = (HA_DIR / "comfortzone-mobile-card.yaml").read_text(encoding="utf-8-sig").strip()

    responsive = "\n".join(
        [
            "type: vertical-stack",
            "cards:",
            conditional_card("(min-width: 1400px)", desktop),
            conditional_card("(min-width: 600px) and (max-width: 1399px)", tablet),
            conditional_card("(max-width: 599px)", mobile),
        ]
    )

    (HA_DIR / "comfortzone-card.yaml").write_text(responsive + "\n", encoding="utf-8")

    dashboard = (
        "title: Comfortzone EX\n"
        "views:\n"
        "  - title: Wärmepumpe\n"
        "    path: waermepumpe\n"
        "    icon: mdi:heat-pump\n"
        "    type: panel\n"
        "    cards:\n"
        f"{indent(as_list_item(responsive), 6)}\n"
    )
    (HA_DIR / "comfortzone-dashboard.yaml").write_text(dashboard, encoding="utf-8")


if __name__ == "__main__":
    main()
