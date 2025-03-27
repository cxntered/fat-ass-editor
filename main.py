import argparse
import os
from collections import Counter
from typing import List

import ass
import questionary
from ass import Style
from ass.data import Color
from questionary import Choice, ValidationError, Validator


def main():
    args = parse_args()

    file_path = UserInteraction.get_file_path(args)
    ass_file = ASSFile(file_path)

    search_type = UserInteraction.get_search_type(args)
    chosen_styles = UserInteraction.get_chosen_styles(ass_file, search_type, args)
    UserInteraction.replace_style_attributes_prompt(ass_file, chosen_styles, args)    


class ASSFile:
    def __init__(self, file_path):
        self.file_path = file_path
        with open(self.file_path, encoding="utf-8-sig") as f:
            self.ass_file = ass.parse(f)
    
    def get_font_names(self):
        return [style.fontname for style in self.ass_file.styles]

    def find_styles_by_font(self, font_name):
        return [style for style in self.ass_file.styles if style.fontname == font_name]

    def find_most_frequent_font(self):
        return Counter(self.get_font_names()).most_common(1)[0][0]

    def replace_style_attributes(self, chosen_styles: List[Style], replacements: dict):
        """
        Replaces the style attributes for the chosen styles.

        Args:
            self (ASSFile): The ASSFile object.
            chosen_styles (List[Style]): The Styles to be modified.
            replacements (dict): The replacements to be made. Key is the index of the attribute to be replaced.
                Value is the new value to be set. Values can either be a String or a bool.
                If the value is an empty string, it will be ignored.
        """
        
        for replacement_style in chosen_styles:
            style: Style = next((style for style in self.ass_file.styles if style.name == replacement_style.name), None)
            if style is None:
                continue

            for key, value in replacements.items():    
                if isinstance(value, str) and value.strip() != "":
                    if key.endswith("color"):
                        value = StyleModifier.hex_to_ass_color(value)
                    setattr(style, key, value)
                elif isinstance(value, bool):
                    setattr(style, key, value)

        with open(self.file_path, "w", encoding="utf-8-sig") as f:
            self.ass_file.dump_file(f)
            questionary.print(f"✓ Updated .ass file saved to: {self.file_path}", style="bold fg:green")


class UserInteraction:
    @staticmethod
    def get_file_path(args):
        return args.file_path or questionary.path(
            "Enter the path to the file you would like to modify:",
            validate=ASSFileValidator,
        ).unsafe_ask()

    @staticmethod
    def get_search_type(args):
        return args.search_type or questionary.select(
            "How would you like to search for a style?",
            choices=[
                Choice("Search by font name", value="font_name"),
                Choice("Most frequently used font", value="most_frequent"),
                Choice("Select all styles", value="all_styles"),
            ],
        ).unsafe_ask()

    @staticmethod
    def get_chosen_styles(ass_file: ASSFile, search_type, args):
        if search_type == "font_name":
            return UserInteraction.get_styles_by_font(ass_file, args.search_font)
        elif search_type == "most_frequent":
            return UserInteraction.get_most_frequent_styles(ass_file)
        elif search_type == "all_styles":
            return ass_file.ass_file.styles
        
    @staticmethod
    def get_styles_by_font(ass_file: ASSFile, font_name=""):
        font_names = ass_file.get_font_names()
        font_name = font_name or questionary.autocomplete(
            "Enter the font name:",
            choices=list(set(font_names)),
            validate=lambda font: True if font in font_names else "No styles found.",
        ).unsafe_ask()
        styles = ass_file.find_styles_by_font(font_name)
        return UserInteraction.select_style(styles) if len(styles) > 1 else styles

    @staticmethod
    def get_most_frequent_styles(ass_file: ASSFile):
        font_name = ass_file.find_most_frequent_font()
        questionary.print(f"ℹ Most frequently used font: {font_name}", style="bold fg:blue")
        styles = ass_file.find_styles_by_font(font_name)
        return UserInteraction.select_style(styles) if len(styles) > 1 else styles
        
    @staticmethod
    def select_style(styles: List[Style]):
        """Allows user to select a specific style or all styles."""
        choices = ["All styles"] + [style.name for style in styles]
        selection = questionary.select(
            "Multiple styles found. Choose one:", choices=choices
        ).unsafe_ask()
        return styles if selection == "All styles" else [style for style in styles if style.fontname == selection]

    @staticmethod
    def replace_style_attributes_prompt(ass_file: ASSFile, chosen_styles, args):
        replace_type = args.replace_type or questionary.select(
            "What would you like to replace?",
            choices=[Choice("Font name", value="font_name"), Choice("Everything", value="everything")],
        ).unsafe_ask()
        replacements = StyleModifier.get_replacements(replace_type, args)
        ass_file.replace_style_attributes(chosen_styles, replacements)


class StyleModifier:
    @staticmethod
    def get_replacements(replace_type, args):
        if replace_type == "font_name":
            return {"fontname": args.font_name or questionary.text("Enter the new font name:").unsafe_ask()}

        return {
            "fontname": args.font_name or questionary.text("New font name (enter to skip):", default="").unsafe_ask(),
            "fontsize": args.font_size or questionary.text("New font size (enter to skip):", default="").unsafe_ask(),
            "primary_color": args.color or questionary.text("New primary hex color (enter to skip):", validate=HexCodeValidator, default="").unsafe_ask(),
            "secondary_color": args.secondary_color or questionary.text("New secondary hex color (enter to skip):", validate=HexCodeValidator, default="").unsafe_ask(),
            "outline_color": args.outline_color or questionary.text("New outline hex color (enter to skip):", validate=HexCodeValidator, default="").unsafe_ask(),
            "back_color": args.back_color or questionary.text("New back hex color (enter to skip):", validate=HexCodeValidator, default="").unsafe_ask(),
            "bold": args.bold or questionary.select("Make text bold?", choices=[Choice("Yes", value=True), Choice("No", value=False), Choice("Skip", value="")]).unsafe_ask(),
            "italic": args.italic or questionary.select("Make text italic?", choices=[Choice("Yes", value=True), Choice("No", value=False), Choice("Skip", value="")]).unsafe_ask(),
            "underline": args.underline or questionary.select("Underline text?", choices=[Choice("Yes", value=True), Choice("No", value=False), Choice("Skip", value="")]).unsafe_ask(),
            "strikeout": args.strikeout or questionary.select("Strikeout text?", choices=[Choice("Yes", value=True), Choice("No", value=False), Choice("Skip", value="")]).unsafe_ask(),
            "outline": args.outline_thickness or questionary.text("Outline thickness (enter to skip):", default="").unsafe_ask(),
            "shadow": args.shadow_distance or questionary.text("Shadow distance (enter to skip):", default="").unsafe_ask()
        }

    @staticmethod
    def hex_to_ass_color(hex_color):
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return Color(r, g, b, 255)


class HexCodeValidator(Validator):
    def validate(self, document):
        if not document.text:
            return True
        hex_code = document.text.lstrip("#")
        if len(hex_code) != 6 or not all(c in "0123456789abcdefABCDEF" for c in hex_code):
            raise ValidationError(message="Invalid hex color code.", cursor_position=len(document.text))


class ASSFileValidator(Validator):
    def validate(self, document):
        if not os.path.isfile(document.text):
            raise ValidationError(message="Please enter a valid ASS file path.")
        if not document.text.endswith(".ass"):
            raise ValidationError(message="File is not an ASS file.")


def parse_args():
    def str_to_bool(value):
        if isinstance(value, bool):
            return value
        if value.lower() in ('true', 'yes', 't', 'y', '1'):
            return True
        elif value.lower() in ('false', 'no', 'f', 'n', '0'):
            return False
        elif value.lower() == "":
            return ""
        else:
            raise argparse.ArgumentTypeError('Boolean value expected.')

    parser = argparse.ArgumentParser(description="Modify .ass subtitle styles via CLI or interactive prompts.")
    parser.add_argument("file_path", nargs="?", help="Path to the .ass file.")
    parser.add_argument("--search-type", choices=["font_name", "most_frequent", "all_styles"], help="Method to search for styles.")
    parser.add_argument("--search-font", help="Font name to search for (if using 'font_name' search type).")
    parser.add_argument("--replace-type", choices=["font_name", "everything"], help="What to replace in styles.")
    parser.add_argument("--font-name", default="", help="New font name.")
    parser.add_argument("--font-size", default="", help="New font size.")
    parser.add_argument("--color", default="", help="New primary hex color code.")
    parser.add_argument("--secondary-color", default="", help="New secondary hex color code.")
    parser.add_argument("--outline-color", default="", help="New outline hex color code.")
    parser.add_argument("--back-color", default="", help="New back hex color code.")
    parser.add_argument("--bold", default="", type=str_to_bool, nargs='?', const=True, help="Make text bold.")
    parser.add_argument("--italic", default="", type=str_to_bool, nargs='?', const=True, help="Make text italic.")
    parser.add_argument("--underline", default="", type=str_to_bool, nargs='?', const=True, help="Underline text.")
    parser.add_argument("--strikeout", default="", type=str_to_bool, nargs='?', const=True, help="Strikeout text.")
    parser.add_argument("--outline-thickness", default="", help="New outline thickness.")
    parser.add_argument("--shadow-distance", default="", help="New shadow distance.")
    return parser.parse_args()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        questionary.print("Operation cancelled by user. Exiting...", style="fg:red")
