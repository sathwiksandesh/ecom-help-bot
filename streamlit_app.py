# app/streamlit_app.py

import streamlit as st
from neo4j import GraphDatabase

# Neo4j config
URI = "bolt://localhost:7687"  # Use Neo4j Aura bolt URL if cloud
USER = "neo4j"
PASSWORD = "neo4j12345" 

# Neo4j driver
driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))


# === Query for product features ===
def get_product_features(tx, product_name):
    query = """
    MATCH (p:Product)-[:hasFeature]->(f:Feature)
    WHERE toLower(p.name) CONTAINS toLower($name)
    RETURN p.name AS name, collect(f.name) AS features
    """
    result = tx.run(query, name=product_name)
    return result.single()


# === Query for FAQ answer ===
def get_faq_answer(tx, question_text):
    query = """
    MATCH (q:FAQ)-[:hasAnswer]->(a:Answer)
    WHERE toLower(q.question) CONTAINS toLower($question)
    RETURN q.question AS q, a.text AS answer
    """
    result = tx.run(query, question=question_text)
    return result.single()


# === Generate Bot Response ===
def get_bot_response(user_input):
    with driver.session() as session:
        # Try product match
        product_data = session.execute_read(get_product_features, user_input)
        if product_data:
            return f"📦 **{product_data['name']}** has features:\n- " + "\n- ".join(product_data["features"])

        # Try FAQ match
        faq_data = session.execute_read(get_faq_answer, user_input)
        if faq_data:
            return f"📘 **Q:** {faq_data['q']}\n🧾 **A:** {faq_data['answer']}"

        return "❌ Sorry, I couldn't find anything for that."


# === Streamlit UI ===
st.set_page_config(page_title="🛒 E-Com Help Bot", layout="centered")
st.title("🛍️ AI Help Bot for E-commerce")

# Session state for chat history
if "chat" not in st.session_state:
    st.session_state.chat = []

# Chat input
user_query = st.text_input("Ask me anything about products or orders:", "")

if user_query:
    bot_reply = get_bot_response(user_query)
    st.session_state.chat.append(("You", user_query))
    st.session_state.chat.append(("Bot", bot_reply))

# Show chat history
for sender, msg in st.session_state.chat[::-1]:
    st.markdown(f"**{sender}:** {msg}")

