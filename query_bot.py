from neo4j import GraphDatabase
import re

# === Neo4j Config ===
URI = "bolt://localhost:7687"
USER = "neo4j"
PASSWORD = "neo4j12345"

try:
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    driver.verify_connectivity()
    print("✅ Connected to Neo4j database.")
except Exception as e:
    print(f"❌ Failed to connect: {e}")
    exit()


# === Utility Functions ===

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
    return set(keywords)


# === Query Functions ===

def get_product_features(product_name):
    escaped_name = re.escape(product_name.lower())
    pattern = ".*" + ".*".join(escaped_name.split()) + ".*"
    query = f"""
    MATCH (p:Product)-[:hasFeature]->(f:Feature)
    WHERE toLower(p.name) =~ '{pattern}'
    RETURN p.name AS product, collect(f.name) AS features
    """
    try:
        with driver.session() as session:
            result = session.run(query)
            records = result.data()
            if not records:
                return f"❌ No features found for '{product_name}'."
            return "\n".join([
                f"✅ Product: {r['product']} has features: {', '.join(r['features'])}"
                for r in records
            ])
    except Exception as e:
        return f"⚠️ Error: {e}"


def get_product_price(product_name):
    escaped_name = re.escape(product_name.lower())
    pattern = ".*" + ".*".join(escaped_name.split()) + ".*"
    query = f"""
    MATCH (p:Product)
    WHERE toLower(p.name) =~ '{pattern}'
    RETURN p.name AS product, p.price AS price
    """
    try:
        with driver.session() as session:
            result = session.run(query)
            records = result.data()
            if not records:
                return f"❌ No price info for '{product_name}'."
            return "\n".join([
                f"💲 Price of {r['product']} is ${r['price']:.2f}"
                for r in records
            ])
    except Exception as e:
        return f"⚠️ Error: {e}"


def list_products_in_category(category):
    query = """
    MATCH (p:Product)-[:belongsTo]->(c:Category)
    WHERE toLower(c.name) CONTAINS toLower($category)
    RETURN c.name AS category, collect(p.name) AS products
    """
    try:
        with driver.session() as session:
            result = session.run(query, category=category)
            records = result.data()
            if not records:
                return f"❌ No products found in category '{category}'."
            return "\n".join([
                f"📦 Products in '{r['category']}': {', '.join(r['products'])}"
                for r in records
            ])
    except Exception as e:
        return f"⚠️ Error: {e}"


def get_faq_answer(keywords):
    query = """
    MATCH (q:FAQ)-[:hasAnswer]->(a:Answer)
    RETURN q.question AS question, a.text AS answer
    """
    try:
        with driver.session() as session:
            result = session.run(query)
            faqs = result.data()

            best_match = None
            best_score = 0

            for faq in faqs:
                faq_words = set(re.findall(r'\b\w+\b', faq["question"].lower()))
                score = len(faq_words.intersection(keywords))
                if score > best_score:
                    best_score = score
                    best_match = faq

            if best_match and best_score > 0:
                return f"📘 Q: {best_match['question']}\n📖 A: {best_match['answer']}"
            return None

    except Exception as e:
        return f"⚠️ FAQ Error: {e}"


# === Main Bot Loop ===

def main():
    print("🤖 Welcome to the E-commerce AI Help Bot!")
    print("Type your query about products, categories, or general FAQs.")
    print("Type 'exit' to quit.\n")

    while True:
        q = input("You: ").strip().lower()

        if q in ["exit", "quit", "bye"]:
            print("Bot: 👋 Goodbye!")
            break
        elif any(word in q for word in ["hello", "hi", "hey"]):
            print("Bot: 👋 Hi! How can I assist you today?")
        elif "return" in q or "refund" in q:
            print("Bot: 🔄 You can return items from 'My Orders' if eligible.")
        elif "help" in q:
            print("Bot: 🆘 I can assist with product features, prices, categories, and FAQs.")
        elif "warranty" in q:
            print("Bot: 🛡️ Warranty info is usually listed in product details.")
        elif "feature" in q or "spec" in q:
            name = extract_product_name(q)
            print("Bot:", get_product_features(name))
        elif "price" in q or "cost" in q:
            name = extract_product_name(q)
            print("Bot:", get_product_price(name))
        elif "product" in q and "in" in q:
            match = re.search(r"in\s+(.+)", q)
            category = match.group(1) if match else ""
            print("Bot:", list_products_in_category(category))
        else:
            keywords = extract_faq_keywords(q)
            answer = get_faq_answer(keywords)
            if answer:
                print("Bot:", answer)
            else:
                print("Bot: 🤔 Sorry, I couldn't find anything. Try asking differently!")


if __name__ == "__main__":
    main()
