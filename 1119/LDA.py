import pandas as pd
import jieba
import re
from sklearn.feature_extraction.text import CountVectorizer
from gensim import corpora, models
import pyLDAvis.gensim_models as gensimvis
import pyLDAvis

# 加载停用词列表
def load_stopwords(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        stopwords = [line.strip() for line in f.readlines()]
    return stopwords

# 停用词文件路径
stopwords_file = "stopwords.txt"
stopwords = load_stopwords(stopwords_file)

# 读取评论数据
with open("disney_comments.txt", "r", encoding="utf-8") as f:
    comments = f.readlines()

# 转为 DataFrame
df = pd.DataFrame(comments, columns=["comment"])

# 文本预处理：清除标点和特殊字符
def preprocess(text):
    text = re.sub(r"[^\w\s]", "", text)  # 去掉标点
    return " ".join(jieba.cut(text.strip()))  # 分词

df["processed_comment"] = df["comment"].apply(preprocess)

# 创建词袋模型，设置停用词和频率限制
vectorizer = CountVectorizer(max_df=0.8, min_df=5, stop_words=stopwords)
X = vectorizer.fit_transform(df["processed_comment"])
vocab = vectorizer.get_feature_names_out()

# 转换为 Gensim 格式
texts = [text.split() for text in df["processed_comment"]]
dictionary = corpora.Dictionary(texts)
corpus = [dictionary.doc2bow(text) for text in texts]

# LDA 模型训练
num_topics = 5
lda_model = models.LdaModel(corpus, num_topics=num_topics, id2word=dictionary, passes=15)

# 输出主题关键词
print("主题关键词：")
for idx, topic in lda_model.print_topics(num_words=10):
    print(f"主题 {idx + 1}: {topic}")

# 生成可视化
print("生成 LDA 可视化...")
lda_vis = gensimvis.prepare(lda_model, corpus, dictionary)
pyLDAvis.save_html(lda_vis, "lda_visualization_cleaned.html")
print("LDA 分析完成！请查看生成的文件 'lda_visualization_cleaned.html'")