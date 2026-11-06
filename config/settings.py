import os

BASE_LOG_DIR = "works"
CSS_STYLES = """
<style>
.output-text { font-family: 'Georgia', serif; font-size: 1.1rem; line-height: 1.6; }
textarea[aria-label='Input (Japanese)'], textarea[aria-label='Editable Translation'] { height: 70vh !important; }
textarea[aria-label='Edit Original Text'], textarea[aria-label='Edit Translated Text'] { 
    font-family: 'Georgia', serif !important; 
    font-size: 1.1rem !important; 
    line-height: 1.6 !important; 
    height: 70vh !important; 
}

/* Tighten the main content container: less vertical padding and a wider
   max-width so the two columns get more room. */
.stMainBlockContainer.block-container {
    padding-top: 1rem !important;
    padding-bottom: 1rem !important;
    max-width: 100% !important;
}

/* Reduce vertical gaps between stacked elements (headers, inputs, buttons). */
.stMainBlockContainer.block-container > * {
    margin-top: 0.25rem !important;
    margin-bottom: 0.25rem !important;
}

/* Tighten the gap above and below dividers. */
hr {
    margin-top: 0.5rem !important;
    margin-bottom: 0.5rem !important;
}

/* Subheaders and h5 labels: less vertical breathing room. */
h3, h5 {
    margin-top: 0.25rem !important;
    margin-bottom: 0.25rem !important;
}

/* Hide the invisible spacer block that Streamlit renders in the sidebar.
   This is the wrapper around the default stSidebarNav (which we don't use
   in this single-page app). We hide it two ways for robustness across
   Streamlit versions: by the emotion-cache hash and via :has() on testid. */
.st-emotion-cache-10p9htt.e15rayve4 {
    display: none !important;
}
[data-testid="stSidebarContent"] > div:has(> [data-testid="stSidebarNav"]) {
    display: none !important;
}
</style>
"""

# Create base directory
if not os.path.exists(BASE_LOG_DIR):
    os.makedirs(BASE_LOG_DIR)