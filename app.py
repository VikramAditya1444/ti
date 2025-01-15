import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import requests
from bs4 import BeautifulSoup
from collections import Counter
import re

# Configure page
st.set_page_config(
    page_title="TradeIndia Product Optimizer",
    page_icon="🛍️",
    layout="wide"
)

# Custom CSS for better UI
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #FF6B6B;
        color: white;
    }
    .css-1d391kg {
        padding: 2rem;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

def initialize_gemini():
    """Initialize Gemini AI with your API key"""
    GOOGLE_API_KEY = "AIzaSyA4CaD8a_dyklJOdrVbQV9y-khbF2LUrsU"
    genai.configure(api_key=GOOGLE_API_KEY)
    return genai.GenerativeModel('gemini-pro')

def get_google_search_results(query, num_results=5):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}&num={num_results}"
    response = requests.get(search_url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    links = []
    for g in soup.find_all("div", class_="tF2Cxc"):
        link = g.find("a", href=True)
        if link:
            links.append(link['href'])
        if len(links) == num_results:
            break
    return links

def scrape_specifications(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")
        
        specs = []
        tables = soup.find_all("table")
        for table in tables:
            for row in table.find_all("tr"):
                cells = row.find_all(["td", "th"])
                if len(cells) >= 2:
                    spec_name = re.sub(r"\s+", " ", cells[0].text.strip())
                    spec_value = re.sub(r"\s+", " ", cells[1].text.strip())
                    specs.append(f"{spec_name}: {spec_value}")
        
        if not specs:
            lists = soup.find_all("ul")
            for ul in lists:
                for li in ul.find_all("li"):
                    text = li.get_text(separator=" ").strip()
                    if ":" in text or "-" in text:
                        specs.append(text)
        
        return specs
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return []

def aggregate_specifications(specifications):
    all_specs = [spec for site_specs in specifications for spec in site_specs]
    spec_counter = Counter(all_specs)
    return spec_counter.most_common()

def generate_specifications(product_description):
    model = initialize_gemini()
    
    prompt = f"""
    Act as an e-commerce product specification expert. Analyze this product description and create detailed specifications 
    that would be relevant for selling on platforms like Amazon, Flipkart, and IndiaMART.

    Product Description: {product_description}

    Create a comprehensive JSON structure with relevant specification categories and fields specifically for this type of product.
    Include all important specifications that buyers typically look for in this kind of product.
    
    Important:
    1. Create category names and field names that are specific to this product type
    2. Use empty strings for values that aren't mentioned in the description
    3. Include standard e-commerce fields like brand, model, etc.
    4. Add category-specific fields (e.g., fabric type for clothing, motor power for machines)
    5. Include all relevant measurements and technical details

    Return only a valid JSON object without any additional text or formatting.
    """
    
    try:
        response = model.generate_content(prompt)
        parts = [part.text for part in response.parts]
        response_text = ''.join(parts)
        
        clean_text = response_text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text.replace("```json", "").replace("```", "").strip()
        elif clean_text.startswith("```"):
            clean_text = clean_text.replace("```", "").strip()
        
        specs = json.loads(clean_text)
        return specs
    
    except Exception as e:
        st.error(f"Error: {str(e)}")
        st.text("Raw response for debugging:")
        st.code(response_text if 'response_text' in locals() else "No response text available")
        return None

def main():
    # Header with logo and title
    col1, col2 = st.columns([1, 4])
    with col1:
        st.image("https://via.placeholder.com/150x80?text=TradeIndia", width=150)
    with col2:
        st.title("Product Specification Optimizer")
        st.subheader("Generate and Compare Product Specifications")

    # Create tabs for different functionalities
    tab1, tab2, tab3 = st.tabs(["AI Generator", "Market Research", "Generated Specifications"])

    # Tab 1: AI Generator
    with tab1:
        st.markdown("### 📸 Upload Product Image")
        uploaded_file = st.file_uploader("Choose a product image", type=['png', 'jpg', 'jpeg'])
        
        if uploaded_file:
            col1, col2 = st.columns(2)
            with col1:
                st.image(uploaded_file, caption="Uploaded Product Image", use_container_width=True)
            with col2:
                st.info("Image processing is currently disabled to optimize performance")

        st.markdown("### 📝 Product Description")
        product_description = st.text_area(
            "Describe your product in detail",
            height=200,
            placeholder="Enter a detailed description of your product including its features, uses, and any specific characteristics..."
        )

        if st.button("Generate Specifications 🚀"):
            if product_description:
                with st.spinner("Analyzing product details..."):
                    specifications = generate_specifications(product_description)
                    if specifications:
                        st.session_state['specifications'] = specifications
                        st.success("Specifications generated successfully! Check the 'Generated Specifications' tab.")
            else:
                st.warning("Please provide a product description.")

    # Tab 2: Market Research
    with tab2:
        with st.form("search_form"):
            user_query = st.text_input("Enter the product name:", placeholder="e.g., paper cutting machine")
            submit_button = st.form_submit_button("Search and Scrape")
        
        if submit_button:
            if not user_query.strip():
                st.warning("⚠️ Please enter a valid product name.")
                return
            
            query = f"{user_query} buy"
            st.info("🔍 Searching for top results...")
            top_links = get_google_search_results(query)
            
            if not top_links:
                st.error("❌ No results found. Please try a different query.")
                return
            
            # Display top results
            st.markdown("### Top Search Results:")
            for i, link in enumerate(top_links, start=1):
                st.markdown(f"- **{i}.** [Visit Site]({link})")
            
            st.info("🛠️ Scraping specifications...")
            specifications = {}
            for link in top_links:
                site_specs = scrape_specifications(link)
                if site_specs:
                    specifications[link] = site_specs
            
            if not specifications:
                st.error("❌ No specifications could be scraped. Please try again.")
                return
            
            # Display site-wise specifications
            st.markdown("## 📋 Specifications from Each Site:")
            for site, specs in specifications.items():
                with st.expander(f"Specifications from {site}"):
                    for spec in specs:
                        st.markdown(f"- {spec}")
            
            # Aggregated results
            aggregated_specs = aggregate_specifications(specifications.values())
            st.markdown("## 🔗 Top Aggregated Specifications:")
            for spec, count in aggregated_specs:
                st.markdown(f"- **{spec}** (found **{count}** times)")

    # Tab 3: Generated Specifications
    with tab3:
        if 'specifications' in st.session_state:
            st.markdown("### 🎯 Optimized Product Specifications")
            
            # Initialize session state for edited specifications if not exists
            if 'edited_specifications' not in st.session_state:
                st.session_state['edited_specifications'] = st.session_state['specifications'].copy()
            
            specs = st.session_state['edited_specifications']
            
            # Create a form for all specifications
            with st.form("specifications_form"):
                for category, details in specs.items():
                    st.markdown(f"### {category.replace('_', ' ').title()}")
                    
                    # Create a new dict for this category if it doesn't exist
                    if category not in st.session_state['edited_specifications']:
                        st.session_state['edited_specifications'][category] = {}
                    
                    # Handle both dictionary and string values
                    if isinstance(details, dict):
                        for key, value in details.items():
                            # If value is empty or "Not specified", show input field with placeholder
                            if not value or value == "" or "not specified" in str(value).lower():
                                specs[category][key] = st.text_input(
                                    f"{key.replace('_', ' ').title()}",
                                    value="" if not value or "not specified" in str(value).lower() else value,
                                    placeholder=f"Enter {key.replace('_', ' ').lower()} here..."
                                )
                            else:
                                # Show pre-filled input field for existing values
                                specs[category][key] = st.text_input(
                                    f"{key.replace('_', ' ').title()}",
                                    value=value
                                )
                    else:
                        # Handle non-dictionary values
                        specs[category] = st.text_input(
                            f"{category.replace('_', ' ').title()}",
                            value=details if details else "",
                            placeholder=f"Enter {category.replace('_', ' ').lower()} here..."
                        )
                
                # Submit button for the form
                if st.form_submit_button("Update Specifications"):
                    st.session_state['edited_specifications'] = specs
                    st.success("Specifications updated successfully!")
            
            # Export options
            st.markdown("### 📤 Export Options")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Download as JSON"):
                    st.download_button(
                        label="Download JSON",
                        data=json.dumps(st.session_state['edited_specifications'], indent=2),
                        file_name="product_specifications.json",
                        mime="application/json"
                    )
            with col2:
                if st.button("Copy to Clipboard"):
                    st.code(json.dumps(st.session_state['edited_specifications'], indent=2))
                    st.success("Specifications copied to clipboard!")

if __name__ == "__main__":
    main()