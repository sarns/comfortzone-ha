"""Import or compose the responsive Home Assistant dashboard device cards."""

import argparse

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HA_DIR = ROOT / "homeassistant"

CARD_BREAKPOINTS = {
    "desktop": "(min-width: 1400px)",
    "tablet": "(min-width: 600px)",
    "mobile": "(max-width: 599px)",
}


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


def import_dashboard_cards() -> None:
    """Preserve manual card edits made in the combined dashboard file."""
    dashboard_path = HA_DIR / "comfortzone-dashboard.yaml"
    lines = dashboard_path.read_text(encoding="utf-8-sig").splitlines()

    for name, marker in CARD_BREAKPOINTS.items():
        marker_index = next(index for index, line in enumerate(lines) if marker in line)
        card_index = next(
            index
            for index in range(marker_index + 1, len(lines))
            if lines[index].lstrip() == "card:"
        )
        content_indent = len(lines[card_index + 1]) - len(lines[card_index + 1].lstrip())
        content = []
        for line in lines[card_index + 1 :]:
            indentation = len(line) - len(line.lstrip())
            if line.strip() and indentation < content_indent:
                break
            content.append(line[content_indent:] if len(line) >= content_indent else "")

        (HA_DIR / f"comfortzone-{name}-card.yaml").write_text(
            "\n".join(content).rstrip() + "\n", encoding="utf-8"
        )


def generate_dashboard() -> None:
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
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--import-dashboard",
        action="store_true",
        help="copy manual edits from the combined dashboard back to the device cards",
    )
    args = parser.parse_args()
    if args.import_dashboard:
        import_dashboard_cards()
    else:
        generate_dashboard()
