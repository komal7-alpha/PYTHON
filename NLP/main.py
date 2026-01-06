import os
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
import re
import string

# Step 1: Load Excel file
df = pd.read_excel(r"Input.xlsx")   # r-string ensures safe path handling

# Step 2: Create folder to save articles
output_dir = "Text_Files"
os.makedirs(output_dir, exist_ok=True)

# Step 3: Function to extract title and text safely
def extract_article(url):
    for attempt in range(3):  # try up to 3 times
        try:
            response = requests.get(url, timeout=30)  # wait up to 30 seconds
            if response.status_code != 200:
                print(f"Skipped (status {response.status_code}): {url}")
                return None, None

            soup = BeautifulSoup(response.text, "html.parser")

            # Extract title
            title_tag = soup.find("h1")
            title = title_tag.get_text(strip=True) if title_tag else "No Title Found"

            # Extract paragraph text
            paragraphs = soup.find_all("p")
            article_text = " ".join(p.get_text(strip=True) for p in paragraphs)

            if not article_text.strip():
                print(f"No paragraph content found in {url}")
                return None, None

            return title, article_text

        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1} failed for {url}: {e}")
            time.sleep(5)  # wait 5 seconds before retrying

    print(f"All retries failed for {url}")
    return None, None

# Step 4: Iterate through URLs and save text files
for index, row in df.iterrows():
    url_id = row["URL_ID"]
    url = row["URL"]

    title, content = extract_article(url)

    if content:
        file_path = os.path.join(output_dir, f"{url_id}.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(title + "\n" + content)
        print(f"Saved: {file_path}")
    else:
        print(f"No content for {url_id}")

print("All URLs processed successfully.")


# Step 5: Text Analysis

# Paths to dictionary and stop words folders
master_dict_path = r"MasterDictionary"
stopwords_folder = r"StopWords"

# Load positive and negative words
positive_words = set(open(os.path.join(master_dict_path, "positive-words.txt"), encoding="utf-8").read().split())
negative_words = set(open(os.path.join(master_dict_path, "negative-words.txt"), encoding="utf-8").read().split())

# Combine all stopwords from multiple files into one set
stop_words = set()
for file in os.listdir(stopwords_folder):
    if file.endswith(".txt"):
        with open(os.path.join(stopwords_folder, file), encoding="latin-1") as f:
            stop_words.update(f.read().split())

# Step 6: To clean text, count words, and calculate metrics
def clean_text(text):
    text = text.lower()
    text = re.sub(r'\n', ' ', text)
    text = re.sub(r'[^a-z\s]', '', text)
    words = [w for w in text.split() if w not in stop_words]
    return words

def count_syllables(word):
    word = word.lower()
    vowels = "aeiou"
    count = sum(1 for char in word if char in vowels)
    if word.endswith("es") or word.endswith("ed"):
        count -= 1
    return max(count, 1)

# Step 7: Process Each Extracted .txt File
output_data = []

for file in os.listdir(output_dir):
    if not file.endswith(".txt"):
        continue

    url_id = file.replace(".txt", "")
    url = df.loc[df["URL_ID"] == url_id, "URL"].values[0] if url_id in df["URL_ID"].astype(str).values else ""

    with open(os.path.join(output_dir, file), encoding="latin-1") as f:
        text = f.read()

    words = clean_text(text)

    positive_score = sum(1 for w in words if w in positive_words)
    negative_score = sum(1 for w in words if w in negative_words)

    polarity_score = (positive_score - negative_score) / ((positive_score + negative_score) + 1e-6)
    subjectivity_score = (positive_score + negative_score) / (len(words) + 1e-6)

    sentences = re.split(r'[.!?]', text)
    sentences = [s for s in sentences if len(s.strip()) > 0]
    avg_sentence_length = len(words) / max(len(sentences), 1)
    avg_number_of_words_per_sentence = avg_sentence_length  # same metric but included as separate column

    complex_words = [w for w in words if count_syllables(w) > 2]
    complex_word_count = len(complex_words)
    percentage_complex_words = complex_word_count / max(len(words), 1)
    fog_index = 0.4 * (avg_sentence_length + percentage_complex_words * 100)

    word_count = len(words)
    syllables_per_word = sum(count_syllables(w) for w in words) / max(word_count, 1)
    personal_pronouns = len(re.findall(r'\b(I|we|my|ours|us)\b', text, re.I))
    avg_word_length = sum(len(w) for w in words) / max(word_count, 1)

    output_data.append([
        url_id, url, positive_score, negative_score, polarity_score, subjectivity_score,
        avg_sentence_length, percentage_complex_words, fog_index,
        avg_number_of_words_per_sentence, complex_word_count, word_count,
        syllables_per_word, personal_pronouns, avg_word_length
    ])

# Step 8: Final Output
columns = [
    "URL_ID", "URL", "POSITIVE SCORE", "NEGATIVE SCORE", "POLARITY SCORE", "SUBJECTIVITY SCORE",
    "AVG SENTENCE LENGTH", "PERCENTAGE OF COMPLEX WORDS", "FOG INDEX",
    "AVG NUMBER OF WORDS PER SENTENCE", "COMPLEX WORD COUNT", "WORD COUNT",
    "SYLLABLE PER WORD", "PERSONAL PRONOUNS", "AVG WORD LENGTH"
]

output_df = pd.DataFrame(output_data, columns=columns)
output_df.to_excel("Output.xlsx", index=False)
print("Completed — Output.xlsx generated successfully!")