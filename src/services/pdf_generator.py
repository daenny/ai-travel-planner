import base64
import sys
from enum import Enum
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS

from src.models import Itinerary


class PDFStyle(str, Enum):
    MAGAZINE = "magazine"
    MINIMAL = "minimal"
    GUIDEBOOK = "guidebook"


class PDFGenerator:
    """Service for generating PDF travel itineraries."""

    def __init__(
        self,
        templates_dir: Path | str = "src/templates",
        exports_dir: Path | str = "exports",
    ):
        self.templates_dir = Path(templates_dir)
        self.exports_dir = Path(exports_dir)
        self.exports_dir.mkdir(parents=True, exist_ok=True)

        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=True,
        )
        self.env.filters["b64image"] = self._image_to_base64

    def _image_to_base64(self, image_path: str | Path | None) -> str:
        """Convert an image file to base64 data URI."""
        if not image_path:
            return ""

        path = Path(image_path)
        if not path.exists():
            return ""

        try:
            data = path.read_bytes()
            ext = path.suffix.lower()
            mime_types = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".gif": "image/gif",
                ".webp": "image/webp",
            }
            mime_type = mime_types.get(ext, "image/jpeg")
            b64 = base64.b64encode(data).decode("utf-8")
            return f"data:{mime_type};base64,{b64}"
        except Exception:
            return ""

    def _generate_qr_code(self, url: str) -> str:
        """Generate a QR code as base64 data URI."""
        try:
            import qrcode
            from io import BytesIO

            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=4,
                border=2,
            )
            qr.add_data(url)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
            return f"data:image/png;base64,{b64}"
        except Exception:
            return ""

    def generate_pdf(
        self,
        itinerary: Itinerary,
        style: PDFStyle = PDFStyle.MAGAZINE,
        output_name: str | None = None,
    ) -> Path:
        """
        Generate a PDF from an itinerary.

        Args:
            itinerary: The itinerary to render
            style: PDF style (magazine, minimal, guidebook)
            output_name: Optional custom output filename

        Returns:
            Path to the generated PDF
        """
        template_name = f"{style.value}.html"
        template = self.env.get_template(template_name)

        qr_codes = {}
        if style == PDFStyle.GUIDEBOOK:
            for day in itinerary.days:
                for activity in day.activities:
                    if activity.booking_link:
                        qr_codes[activity.booking_link] = self._generate_qr_code(
                            activity.booking_link
                        )

        html_content = template.render(
            itinerary=itinerary,
            qr_codes=qr_codes,
            b64image=self._image_to_base64,
        )

        if output_name is None:
            safe_title = "".join(
                c if c.isalnum() or c in "._- " else "_" for c in itinerary.title
            )
            output_name = f"{safe_title}_{style.value}"

        output_path = self.exports_dir / f"{output_name}.pdf"

        html = HTML(string=html_content, base_url=str(self.templates_dir))
        html.write_pdf(output_path)

        return output_path

    def generate_all_styles(self, itinerary: Itinerary) -> dict[PDFStyle, Path]:
        """
        Generate PDFs in all available styles.

        Args:
            itinerary: The itinerary to render

        Returns:
            Dict mapping style to generated PDF path
        """
        results = {}
        for style in PDFStyle:
            results[style] = self.generate_pdf(itinerary, style)
        return results
