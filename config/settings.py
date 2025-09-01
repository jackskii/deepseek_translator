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
</style>
"""

# Create base directory
if not os.path.exists(BASE_LOG_DIR):
    os.makedirs(BASE_LOG_DIR)