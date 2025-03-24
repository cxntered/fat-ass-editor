import questionary
from questionary import Choice, Validator, ValidationError
import argparse
import os

def main():
    args = parse_args()

    file_path = UserInteraction.get_file_path(args)
    ass_file = ASSFile(file_path)

    search_type = UserInteraction.get_search_type(args)
    chosen_styles = UserInteraction.get_chosen_styles(ass_file, search_type, args)
    UserInteraction.replace_style_attributes_prompt(ass_file, chosen_styles, args)
    
    questionary.print(f"✓ Updated .ass file saved to: {file_path}", style="bold fg:green")


class ASSFile:
    def __init__(self, file_path):
        self.file_path = file_path

    def get_fonts(self):
        """
        Extract all font names from the file.
        Returns a list of tuples with font name and the full line.
        """
        
        with open(self.file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        fonts = [(line.split(",")[1].strip(), line) for line in lines if line.startswith("Style:")]
        return fonts

    def find_styles_by_font(self, font_name):
        return [line for font, line in self.get_fonts() if font == font_name]

    def find_most_frequent_font(self):
        fonts = self.get_fonts()
        font_counts = {}
        for font, _ in fonts:
            font_counts[font] = font_counts.get(font, 0) + 1
        return max(font_counts, key=font_counts.get)

    def replace_style_attributes(self, chosen_styles, replacements):
        """
        Replaces the style attributes for the chosen styles.

        Args:
            self (ASSFile): The ASSFile object.
            chosen_styles (list): The styles to be modified. Should be the full line from the file.
            replacements (dict): The replacements to be made. Key is the index of the attribute to be replaced.
                Value is the new value to be set. If the value is a hex color code, it will be converted to a
                Visual Basic hex color code. If the value is an empty string, it will be skipped.
        """
        
        with open(self.file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        in_styles_section = False
        updated_lines = []

        for line in lines:
            if line.strip().startswith("[V4+ Styles]"):
                in_styles_section = True
            elif line.strip().startswith("[") and in_styles_section:
                in_styles_section = False

            if in_styles_section and line.startswith("Style:") and line in chosen_styles:
                parts = line.split(",")
                for index, key in replacements.items():
                    if index < len(parts) and key.strip():
                        parts[index] = key if not key.startswith("#") else StyleModifier.hex_to_ass_color(key)
                line = ",".join(parts)

            updated_lines.append(line)

        with open(self.file_path, "w", encoding="utf-8") as f:
            f.writelines(updated_lines)


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
                Choice("All styles", value="all_styles"),
            ],
        ).unsafe_ask()

    @staticmethod
    def get_chosen_styles(ass_file, search_type, args):
        if search_type == "font_name":
            return UserInteraction.get_styles_by_font(ass_file, args.font_name)
        elif search_type == "most_frequent":
            return UserInteraction.get_most_frequent_styles(ass_file)
        elif search_type == "all_styles":
            return [t[1] for t in ass_file.get_fonts()]
        
    @staticmethod
    def get_styles_by_font(ass_file, font_name=None):
        fonts = ass_file.get_fonts()
        choices = list(set([t[0] for t in fonts]))
        font_name = font_name or questionary.autocomplete(
            "Enter the font name:",
            choices=choices,
            validate=lambda font: True if font in choices else "No styles found.",
        ).unsafe_ask()
        styles = ass_file.find_styles_by_font(font_name)
        return UserInteraction.select_style(styles) if len(styles) > 1 else styles

    @staticmethod
    def get_most_frequent_styles(ass_file):
        font_name = ass_file.find_most_frequent_font()
        questionary.print(f"ℹ Most frequently used font: {font_name}", style="bold fg:blue")
        styles = ass_file.find_styles_by_font(font_name)
        return UserInteraction.select_style(styles) if len(styles) > 1 else styles
        
    @staticmethod
    def select_style(styles):
        """Allows user to select a specific style or all styles."""
        choices = ["All styles"] + [t.split(",")[0].split(":")[1].strip() for t in styles]
        selection = questionary.select(
            "Multiple styles found. Choose one:", choices=choices
        ).unsafe_ask()
        return (
            styles
            if selection == "All styles"
            else [next(s for s in styles if selection in s)]
        )

    @staticmethod
    def replace_style_attributes_prompt(ass_file, chosen_styles, args):
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
            return {1: args.new_font or questionary.text("Enter the new font name:").unsafe_ask()}
        return {
            i: v for i, v in enumerate([
                args.new_font or questionary.text("New font name (enter to skip):", default="").unsafe_ask(),
                args.new_size or questionary.text("New font size (enter to skip):", default="").unsafe_ask(),
                args.new_color or questionary.text("New primary hex color (enter to skip):", validate=HexCodeValidator, default="").unsafe_ask(),
                args.new_secondary_color or questionary.text("New secondary hex color (enter to skip):", validate=HexCodeValidator, default="").unsafe_ask(),
                args.new_outline_color or questionary.text("New outline hex color (enter to skip):", validate=HexCodeValidator, default="").unsafe_ask(),
                args.new_back_color or questionary.text("New back hex color (enter to skip):", validate=HexCodeValidator, default="").unsafe_ask(),
                args.bold or questionary.select("Make text bold?", choices=[Choice("Yes", value="1"), Choice("No", value="0"), Choice("Skip", value="")]).unsafe_ask(),
                args.italic or questionary.select("Make text italic?", choices=[Choice("Yes", value="1"), Choice("No", value="0"), Choice("Skip", value="")]).unsafe_ask(),
                args.underline or questionary.select("Underline text?", choices=[Choice("Yes", value="1"), Choice("No", value="0"), Choice("Skip", value="")]).unsafe_ask(),
                args.strikeout or questionary.select("Strikeout text?", choices=[Choice("Yes", value="1"), Choice("No", value="0"), Choice("Skip", value="")]).unsafe_ask(),
                args.outline_thickness or questionary.text("Outline thickness (enter to skip):", default="").unsafe_ask(),
                args.shadow_distance or questionary.text("Shadow distance (enter to skip):", default="").unsafe_ask()
            ], start=1) if v.strip()
        }

    @staticmethod
    def hex_to_ass_color(hex_color):
        """Convert standard #RRGGBB hex to &HAABBGGRR Visual Basic hex code format"""

        hex_color = hex_color.lstrip("#")
        if len(hex_color) != 6:
            raise ValueError("Invalid hex color format. Use #RRGGBB.")
        return f"&H00{hex_color[4:6]}{hex_color[2:4]}{hex_color[0:2]}".upper()


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
    parser = argparse.ArgumentParser(description="Modify .ass subtitle styles via CLI or interactive prompts.")
    parser.add_argument("file_path", nargs="?", help="Path to the .ass file.")
    parser.add_argument("--search-type", choices=["font_name", "most_frequent", "all_styles"], help="Method to search for styles.")
    parser.add_argument("--font-name", help="Font name to search for (if using 'font_name' search type).")
    parser.add_argument("--replace-type", choices=["font_name", "everything"], help="What to replace in styles.")
    parser.add_argument("--new-font", help="New font name if replacing font.")
    parser.add_argument("--new-size", help="New font size.")
    parser.add_argument("--new-color", help="New primary hex color code.")
    parser.add_argument("--new-secondary-color", help="New secondary hex color code.")
    parser.add_argument("--new-outline-color", help="New outline hex color code.")
    parser.add_argument("--new-back-color", help="New back hex color code.")
    parser.add_argument("--bold", choices=["1", "0"], help="Make text bold (1 for yes, 0 for no).")
    parser.add_argument("--italic", choices=["1", "0"], help="Make text italic (1 for yes, 0 for no).")
    parser.add_argument("--underline", choices=["1", "0"], help="Underline text (1 for yes, 0 for no).")
    parser.add_argument("--strikeout", choices=["1", "0"], help="Strikeout text (1 for yes, 0 for no).")
    parser.add_argument("--outline-thickness", help="New outline thickness.")
    parser.add_argument("--shadow-distance", help="New shadow distance.")
    return parser.parse_args()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        questionary.print("Operation cancelled by user. Exiting...", style="fg:red")
