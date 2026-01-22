"""Blog tips tab renderer for the Travel Planner UI."""

import streamlit as st

from ai_travel_planner.services import BlogScraper


def render_blog_tips():
    """Render extracted blog tips with blog input UI."""
    st.header("📝 Blog Tips")

    # Blog input section at top
    st.subheader("Add Travel Blog")
    col1, col2 = st.columns([3, 1])
    with col1:
        blog_url = st.text_input("Blog URL", placeholder="https://...", key="blog_url_input")
    with col2:
        use_ai_extraction = st.checkbox("Use AI", value=True, key="use_ai_blog", help="Use AI to extract tips intelligently")

    # Button row: Extract Tips and Discover Links
    btn_col1, btn_col2, _ = st.columns([1, 1, 2])
    with btn_col1:
        extract_clicked = st.button("Extract Tips", key="extract_blog")
    with btn_col2:
        discover_clicked = st.button("Discover Links", key="discover_links")

    if extract_clicked:
        if blog_url:
            scraper = BlogScraper()
            agent = st.session_state.agent

            if use_ai_extraction and agent:
                with st.spinner("Extracting with AI (this may take a moment)..."):
                    content = scraper.scrape_with_ai(blog_url, agent)
            else:
                with st.spinner("Extracting content..."):
                    content = scraper.scrape_blog(blog_url)

            if content:
                st.session_state.blog_content[blog_url] = content
                if blog_url not in st.session_state.session.itinerary.blog_urls:
                    st.session_state.session.itinerary.blog_urls.append(blog_url)
                tip_count = len(content.tips)
                st.success(f"Extracted: {content.title} ({tip_count} tips)")
                st.rerun()
            else:
                st.error("Failed to extract content")
        else:
            st.warning("Please enter a blog URL")

    if discover_clicked:
        if blog_url:
            scraper = BlogScraper()
            already_scraped = set(st.session_state.blog_content.keys())
            with st.spinner("Discovering links..."):
                links = scraper.discover_links(blog_url, already_scraped)
            if links:
                st.session_state.discovered_links[blog_url] = links
                st.success(f"Found {len(links)} links")
                st.rerun()
            else:
                st.info("No new links found on this page")
        else:
            st.warning("Please enter a blog URL")

    st.markdown("---")

    # Display extracted blogs
    if st.session_state.blog_content:
        st.subheader(f"Extracted Blogs ({len(st.session_state.blog_content)})")

        urls_to_delete = []
        for url in list(st.session_state.blog_content.keys()):
            content = st.session_state.blog_content[url]
            with st.expander(content.title, expanded=False):
                col1, col2 = st.columns([5, 1])
                with col1:
                    st.markdown(f"**Source:** [{url}]({url})")
                with col2:
                    if st.button("🗑️ Delete", key=f"del_blog_tab_{hash(url)}"):
                        urls_to_delete.append(url)

                st.markdown(f"**Summary:** {content.summary[:300]}...")

                if content.tips:
                    st.markdown("**Tips:**")
                    for tip in content.tips[:5]:
                        st.markdown(f"- {tip}")

                if content.highlights:
                    st.markdown("**Highlights:**")
                    for highlight in content.highlights[:5]:
                        st.markdown(f"- {highlight}")

        # Process deletions after iteration
        for url in urls_to_delete:
            del st.session_state.blog_content[url]
            if url in st.session_state.session.itinerary.blog_urls:
                st.session_state.session.itinerary.blog_urls.remove(url)
            st.success(f"Deleted blog: {url[:50]}...")
            st.rerun()
    else:
        st.info("No blogs added yet. Enter a travel blog URL above to extract tips and highlights.")

    # Display discovered links
    if st.session_state.discovered_links:
        st.markdown("---")
        total_links = sum(len(links) for links in st.session_state.discovered_links.values())
        st.subheader(f"Discovered Links ({total_links})")

        # Initialize selection state if needed
        if "selected_discovered_links" not in st.session_state:
            st.session_state.selected_discovered_links = set()

        # Display links grouped by source URL
        sources_to_clear = []
        for source_url, links in st.session_state.discovered_links.items():
            with st.expander(f"From: {source_url[:60]}... ({len(links)} links)", expanded=True):
                col1, col2 = st.columns([5, 1])
                with col2:
                    if st.button("🗑️ Clear", key=f"clear_discovered_{hash(source_url)}"):
                        sources_to_clear.append(source_url)

                for link in links:
                    # Create unique key for checkbox
                    link_key = f"sel_{hash(link.url)}"
                    is_selected = st.checkbox(
                        link.title[:80] + ("..." if len(link.title) > 80 else ""),
                        key=link_key,
                        help=link.url,
                    )
                    if is_selected:
                        st.session_state.selected_discovered_links.add(link.url)
                    elif link.url in st.session_state.selected_discovered_links:
                        st.session_state.selected_discovered_links.discard(link.url)

        # Clear sources after iteration
        for source in sources_to_clear:
            # Remove selected links that belonged to this source
            links_to_remove = {link.url for link in st.session_state.discovered_links[source]}
            st.session_state.selected_discovered_links -= links_to_remove
            del st.session_state.discovered_links[source]
            st.rerun()

        # Scrape selected button
        selected_count = len(st.session_state.selected_discovered_links)
        if selected_count > 0:
            if st.button(f"Scrape Selected ({selected_count})", key="scrape_selected"):
                scraper = BlogScraper()
                agent = st.session_state.agent if use_ai_extraction else None
                urls_to_scrape = list(st.session_state.selected_discovered_links)

                progress_bar = st.progress(0)
                status_text = st.empty()

                scraped_urls = []
                for i, (url, content, error) in enumerate(scraper.batch_scrape(urls_to_scrape, agent, use_ai_extraction)):
                    progress = (i + 1) / len(urls_to_scrape)
                    progress_bar.progress(progress)
                    status_text.text(f"Scraping {i + 1}/{len(urls_to_scrape)}: {url[:50]}...")

                    if content:
                        st.session_state.blog_content[url] = content
                        if url not in st.session_state.session.itinerary.blog_urls:
                            st.session_state.session.itinerary.blog_urls.append(url)
                        scraped_urls.append(url)
                    elif error:
                        st.warning(f"Failed: {url[:40]}... - {error}")

                # Remove scraped URLs from discovered links
                for source_url in list(st.session_state.discovered_links.keys()):
                    st.session_state.discovered_links[source_url] = [
                        link for link in st.session_state.discovered_links[source_url]
                        if link.url not in scraped_urls
                    ]
                    # Remove source if no links left
                    if not st.session_state.discovered_links[source_url]:
                        del st.session_state.discovered_links[source_url]

                # Clear selection
                st.session_state.selected_discovered_links.clear()

                progress_bar.empty()
                status_text.empty()
                st.success(f"Scraped {len(scraped_urls)} blogs")
                st.rerun()
