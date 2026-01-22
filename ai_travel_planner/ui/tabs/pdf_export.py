"""PDF Export tab renderer for the Travel Planner UI."""

import streamlit as st

from ai_travel_planner.services import UnsplashService, PDFGenerator
from ai_travel_planner.services.pdf_generator import PDFStyle
from ai_travel_planner.ui.config import IMAGES_DIR, EXPORTS_DIR
from ai_travel_planner.ui.api_keys import get_api_key
from ai_travel_planner.ui.helpers import render_settings_prompt


def render_pdf_export(local_mode: bool):
    """Render the PDF export tab."""
    st.header("📄 PDF Export")

    # Check if AI is connected
    if not st.session_state.agent:
        st.info("Connect to an AI provider in Settings to generate itineraries that can be exported to PDF.")
        render_settings_prompt("Go to Settings to connect an AI provider.")
        return

    # Check if itinerary exists
    itinerary = st.session_state.session.itinerary
    if not itinerary.days:
        st.info("No itinerary to export yet. Create an itinerary in the Itinerary tab first, then come back here to export it as a PDF.")
        return

    # Show itinerary summary
    st.subheader(f"Export: {itinerary.title}")
    st.caption(f"{len(itinerary.days)} days | {itinerary.travelers} traveler(s)")
    if itinerary.description:
        st.markdown(itinerary.description)

    st.markdown("---")

    # PDF style selection and generation
    col_style, col_gen, col_all = st.columns([2, 1, 1])
    with col_style:
        pdf_style = st.selectbox(
            "PDF Style",
            [s.value for s in PDFStyle],
            format_func=lambda x: x.title(),
            key="pdf_style_export",
            help="Choose a style for your PDF: Magazine (colorful), Minimal (clean), or Guidebook (print-ready with QR codes)",
        )
    with col_gen:
        generate_pdf_clicked = st.button("Generate PDF", key="gen_pdf_export", type="primary", use_container_width=True)
    with col_all:
        generate_all_clicked = st.button("All Styles", key="gen_all_pdf_export", use_container_width=True)

    # Style descriptions
    with st.expander("Style descriptions"):
        st.markdown("""
        - **Magazine**: Colorful travel magazine style with large photos and vibrant design
        - **Minimal**: Clean, elegant style focused on readability
        - **Guidebook**: Print-optimized with QR codes for locations and practical layout
        """)

    if generate_pdf_clicked:
        with st.spinner("Generating PDF..."):
            _load_photos_if_needed(itinerary, local_mode)

            generator = PDFGenerator(exports_dir=EXPORTS_DIR)
            pdf_path = generator.generate_pdf(
                st.session_state.session.itinerary,
                PDFStyle(pdf_style),
            )
            st.success("PDF generated!")

            with open(pdf_path, "rb") as f:
                st.download_button(
                    "Download PDF",
                    f,
                    file_name=pdf_path.name,
                    mime="application/pdf",
                    key="download_pdf_export",
                )

    if generate_all_clicked:
        with st.spinner("Generating all PDFs..."):
            _load_photos_if_needed(itinerary, local_mode)

            generator = PDFGenerator(exports_dir=EXPORTS_DIR)
            paths = generator.generate_all_styles(st.session_state.session.itinerary)
            st.success("All PDFs generated!")
            for style, path in paths.items():
                with open(path, "rb") as f:
                    st.download_button(
                        f"Download {style.value.title()}",
                        f,
                        file_name=path.name,
                        mime="application/pdf",
                        key=f"dl_export_{style.value}",
                    )


def _load_photos_if_needed(itinerary, local_mode: bool):
    """Load photos for itinerary days if not already loaded."""
    unsplash_api_key = get_api_key("Unsplash", local_mode)
    if not unsplash_api_key:
        return

    unsplash = UnsplashService(unsplash_api_key, IMAGES_DIR)
    for day in itinerary.days:
        # Use AI-generated image queries if available
        if day.image_queries and not day.image_paths:
            paths = unsplash.download_photos_for_queries(
                day.image_queries, max_images=3
            )
            day.image_paths = [str(p) for p in paths]
            # Also set single image_path for backward compatibility
            if paths and not day.image_path:
                day.image_path = str(paths[0])
        # Fallback to location-based single image
        elif not day.image_path and not day.image_paths:
            img_path = unsplash.get_photo_for_location(day.location)
            if img_path:
                day.image_path = str(img_path)
                day.image_paths = [str(img_path)]
