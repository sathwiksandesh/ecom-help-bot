import streamlit as st
from neo4j import GraphDatabase
import re

# Neo4j Config
URI = "bolt://localhost:7687"
USER = "neo4j"
PASSWORD = "neo4j12345"

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

# ---------------- Helper Functions ----------------

def extract_product_name(query):
    patterns = [
        r"(?:features|specs|price|cost|about)\s+of\s+(.+)",
        r"what is the (?:price|cost)\s+of\s+(.+)",
        r"tell me about\s+(.+)",
        r"(.+)\s+features",
        r"(.+)\s+price",
    ]
    for pattern in patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return query.strip()

def extract_faq_keywords(question):
    stop_words = set([
        "a", "an", "the", "what", "how", "do", "i", "me", "my", "can", "is", "are",
        "about", "for", "of", "to", "in", "on", "with", "item", "product"
    ])
    keywords = [
        word for word in re.findall(r'\b\w+\b', question.lower())
        if word not in stop_words and len(word) > 2
    ]
    return keywords

def get_product_features(tx, product_name):
    escaped = re.escape(product_name.lower())
    words = escaped.split()
    pattern = ".*" + ".*".join(words) + ".*"
    query = f"""
    MATCH (p:Product)-[:hasFeature]->(f:Feature)
    WHERE toLower(p.name) =~ '{pattern}'
    RETURN p.name AS product, collect(f.name) AS features
    """
    result = tx.run(query)
    return result.data()

def get_product_price(tx, product_name):
    escaped = re.escape(product_name.lower())
    words = escaped.split()
    pattern = ".*" + ".*".join(words) + ".*"
    query = f"""
    MATCH (p:Product)
    WHERE toLower(p.name) =~ '{pattern}'
    RETURN p.name AS product, p.price AS price
    """
    result = tx.run(query)
    return result.data()

def list_products_by_category(tx, category_name):
    query = """
    MATCH (p:Product)-[:belongsTo]->(c:Category)
    WHERE toLower(c.name) CONTAINS toLower($category)
    RETURN c.name AS category, collect(p.name) AS products
    """
    result = tx.run(query, category=category_name)
    return result.data()

def get_faq_answer(tx, keywords):
    query = """
    MATCH (q:FAQ)-[:hasAnswer]->(a:Answer)
    WHERE ANY(keyword IN $keywords WHERE toLower(q.question) CONTAINS toLower(keyword))
    RETURN q.question AS question, a.text AS answer
    LIMIT 1
    """
    result = tx.run(query, keywords=keywords)
    return result.data()

# ---------------- Streamlit UI ----------------

st.set_page_config(page_title="E-commerce AI Help Bot", page_icon="🛒")
st.title("🛍️ E-commerce AI Help Bot")
st.write("Ask me about **products**, **features**, **prices**, **categories**, or common **FAQs** (returns, shipping, warranty, etc.)")

user_input = st.text_input("Type your query:")

if user_input:
    q_lower = user_input.lower().strip()

    with driver.session() as session:
        response = ""

        if any(word in q_lower for word in ["hi", "hello", "hey", "greetings"]):
            response = "👋 Hi there! How can I assist you today?"

        elif any(word in q_lower for word in ["thank you", "thanks", "thx", "thankyou"]):
            response = "🙏 You're welcome! Let me know if you have any more questions."

        elif "feature" in q_lower or "spec" in q_lower:
            product = extract_product_name(q_lower)
            data = session.read_transaction(get_product_features, product)
            if data:
                for r in data:
                    response += f"📦 **{r['product']}** features:\n- " + "\n- ".join(r["features"])
            else:
                response = f"❌ No features found for: {product}"

        elif "price" in q_lower or "cost" in q_lower or "how much" in q_lower:
            product = extract_product_name(q_lower)
            data = session.read_transaction(get_product_price, product)
            if data:
                for r in data:
                    response += f"💰 **{r['product']}** is priced at ₹{r['price']}"
            else:
                response = f"❌ No pricing found for: {product}"

        elif "category" in q_lower or "in" in q_lower:
            match = re.search(r"in\s+(.+)", q_lower)
            cat = match.group(1).strip() if match else ""
            data = session.read_transaction(list_products_by_category, cat)
            if data:
                for r in data:
                    response += f"🗂️ Products in **{r['category']}**:\n- " + "\n- ".join(r["products"])
            else:
                response = f"❌ No products found in category: {cat}"

        else:
            # Fallback to FAQ
            keywords = extract_faq_keywords(q_lower)
            data = session.read_transaction(get_faq_answer, keywords)
            if data:
                r = data[0]
                response = f"📖 **Q:** {r['question']}\n💬 **A:** {r['answer']}"
            else:
                response = "🤔 I couldn't find an answer. Please rephrase or try a product or category-related query."

        st.markdown(response)
