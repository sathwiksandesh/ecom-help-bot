from neo4j import GraphDatabase
import re # Import regular expressions for better parsing

# === Neo4j Database Config ===
URI = "bolt://localhost:7687"  # Use Neo4j Aura bolt URL if cloud
USER = "neo4j"
PASSWORD = "neo4j12345"  # <- REPLACE WITH YOUR ACTUAL NEO4J PASSWORD

# === Connect to Neo4j ===
try:
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    driver.verify_connectivity() # Test connection immediately
    print("Successfully connected to Neo4j database.")
except Exception as e:
    print(f"Failed to connect to Neo4j: {e}")
    print("Please ensure Neo4j is running and credentials/URI are correct.")
    exit() # Exit if connection fails, as the bot won't work without it


# === Helper Functions ===

def extract_product_name(query):
    """More robust extraction: look for common phrases to get product name."""
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
    return query.strip() # Return original query if no specific pattern found


def extract_faq_keywords(question):
    """Extracts relevant keywords from a user's question for FAQ matching."""
    # Simple list of common English stop words that don't add much to search
    stop_words = set([
        "a", "an", "the", "what", "how", "do", "i", "me", "my", "can", "is", "are",
        "about", "for", "of", "to", "in", "on", "with", "item", "product", "a", "an"
    ])
    # Split question into words, convert to lowercase, and filter out stop words
    keywords = [
        word for word in re.findall(r'\b\w+\b', question.lower())
        if word not in stop_words and len(word) > 2 # Ignore very short words
    ]
    return keywords


# === Neo4j Query Functions ===

def get_product_features(product_name):
    """Retrieves features for a given product name (case-insensitive, more flexible match)."""
    # Use regex for flexible matching: allows for partial words and order variations
    # Escaping special regex characters in product_name
    escaped_product_name = re.escape(product_name)
    # Create a regex pattern that matches if all words from product_name are present anywhere in the product name
    # This is a more flexible approach than strict word boundaries or simple CONTAINS
    keywords = escaped_product_name.lower().split()
    regex_pattern = ".*" + ".*".join(keywords) + ".*"

    query = f"""
    MATCH (p:Product)-[:hasFeature]->(f:Feature)
    WHERE toLower(p.name) =~ '{regex_pattern}'
    RETURN p.name AS product, collect(f.name) AS features
    """
    try:
        with driver.session() as session:
            result = session.run(query) # No need to pass $name if using f-string for regex
            records = result.data()

            if not records:
                return f"No features found for a product matching '{product_name}'. Please try a different name."

            responses = []
            for r in records:
                features = ", ".join(r['features'])
                responses.append(f"Product: {r['product']} has features: {features}")
            return "\n".join(responses)
    except Exception as e:
        return f"An error occurred while fetching features: {e}"


def get_product_price(product_name):
    """Retrieves the price for a given product name (case-insensitive, more flexible match)."""
    # Use regex for flexible matching, similar to get_product_features
    escaped_product_name = re.escape(product_name)
    keywords = escaped_product_name.lower().split()
    regex_pattern = ".*" + ".*".join(keywords) + ".*"

    query = f"""
    MATCH (p:Product)
    WHERE toLower(p.name) =~ '{regex_pattern}'
    RETURN p.name AS product, p.price AS price
    """
    try:
        with driver.session() as session:
            result = session.run(query) # No need to pass $name if using f-string for regex
            records = result.data()

            if not records:
                return f"No price found for a product matching '{product_name}'. Please try a different name."

            responses = []
            for r in records:
                responses.append(f"The price of {r['product']} is ${r['price']:.2f}.")
            return "\n".join(responses)
    except Exception as e:
        return f"An error occurred while fetching the price: {e}"


def list_products_in_category(category_name):
    """Lists products belonging to a given category (case-insensitive, partial match)."""
    query = """
    MATCH (p:Product)-[:belongsTo]->(c:Category)
    WHERE toLower(c.name) CONTAINS toLower($category)
    RETURN c.name AS category, collect(p.name) AS products
    """
    try:
        with driver.session() as session:
            result = session.run(query, category=category_name)
            records = result.data()

            if not records:
                return f"No products found in a category matching '{category_name}'. Please try a different category."

            responses = []
            for r in records:
                products = ", ".join(r['products'])
                responses.append(f"Products in the '{r['category']}' category: {products}")
            return "\n".join(responses)
    except Exception as e:
        return f"An error occurred while listing products: {e}"


def get_faq_answer(keywords):
    """Retrieves an answer for a given FAQ question using keywords (case-insensitive)."""
    # This query checks if ANY of the provided keywords are contained in the FAQ question.
    query = """
    MATCH (q:FAQ)-[:hasAnswer]->(a:Answer)
    WHERE ANY(keyword IN $keywords WHERE toLower(q.question) CONTAINS toLower(keyword))
    RETURN q.question AS question, a.text AS answer
    LIMIT 1 // Limit to one best match for simplicity
    """
    try:
        with driver.session() as session:
            result = session.run(query, keywords=keywords)
            records = result.data()

            if not records:
                return None  # Return None for fallback handling

            r = records[0] # Take the first match
            return f"Q: {r['question']}\nA: {r['answer']}"
    except Exception as e:
        return f"An error occurred while fetching FAQ: {e}"


# === Main Chatbot Logic ===
def main():
    print("Welcome to the E-commerce Chatbot!")
    print("You can ask me about product features, prices, or categories, and general FAQs.")
    print("Try asking: 'What are the features of Laptop X?', 'How much is the Smartphone Y?', 'List products in Electronics', or 'How do I return an item?'")
    print("Type 'exit' to quit.")

    while True:
        q = input("You: ")
        q_lower = q.lower().strip()

        if q_lower == "exit":
            print("Bot: Goodbye! Have a great day!")
            break
        elif any(word in q_lower for word in ["hi", "hello", "hey", "greetings"]):
            print("Bot: Hi there! How can I assist you today?")
        elif any(word in q_lower for word in ["thank you", "thanks", "ok", "okay"]):
            print("Bot: You're welcome! Is there anything else I can help with?")
        elif "feature" in q_lower or "spec" in q_lower:
            product_name = extract_product_name(q_lower)
            print("Bot:", get_product_features(product_name))
        elif "price" in q_lower or "cost" in q_lower or "how much" in q_lower:
            product_name = extract_product_name(q_lower)
            print("Bot:", get_product_price(product_name))
        elif "product" in q_lower and ("category" in q_lower or "in" in q_lower):
            # Simple category extraction (can be improved with more NLP)
            match = re.search(r"in\s+(.+)", q_lower)
            category_name = match.group(1).strip() if match else ""
            if category_name:
                print("Bot:", list_products_in_category(category_name))
            else:
                print("Bot: Please specify the category you're interested in (e.g., 'List products in Electronics').")
        else:
            # Try FAQ as a fallback
            faq_keywords = extract_faq_keywords(q_lower)
            if faq_keywords: # Only query if we have valid keywords
                answer = get_faq_answer(faq_keywords)
                if answer:
                    print("Bot:", answer)
                else:
                    print("Bot: I'm not sure about that. Could you rephrase or ask about product features, prices, categories, or common questions?")
            else: # If no meaningful keywords extracted
                print("Bot: I'm not sure about that. Could you rephrase or ask about product features, prices, categories, or common questions?")


if __name__ == "__main__":
    main()
