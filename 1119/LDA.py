import pandas as pd
import jieba
import re
from sklearn.feature_extraction.text import CountVectorizer
from gensim import corpora, models
import pyLDAvis.gensim_models as gensimvis
import pyLDAvis
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import os

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

# 生成词云
def generate_wordcloud(lda_model, topic_num, font_path='simhei.ttf', output_dir='wordclouds'):
    """
    生成指定主题的词云

    :param lda_model: 训练好的 LDA 模型
    :param topic_num: 主题编号（从0开始）
    :param font_path: 中文字体路径
    :param output_dir: 词云图片保存目录
    """
    # 获取主题的词和权重
    topic = lda_model.show_topic(topic_num, topn=50)
    word_freq = {word: weight for word, weight in topic}

    # 创建词云对象
    wc = WordCloud(
        font_path=font_path,            # 中文字体
        width=800,
        height=600,
        background_color='white',
        max_words=100,
        scale=2,
        random_state=42,
        colormap='viridis'
    )

    wc.generate_from_frequencies(word_freq)

    # 创建保存目录
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 保存词云图片
    output_path = os.path.join(output_dir, f'topic_{topic_num + 1}_wordcloud.png')
    wc.to_file(output_path)
    print(f"主题 {topic_num + 1} 的词云已保存至 {output_path}")

    # 可选：显示词云
    plt.figure(figsize=(10, 8))
    plt.imshow(wc, interpolation='bilinear')
    plt.axis('off')
    plt.title(f"主题 {topic_num + 1} 词云", fontsize=16)
    plt.show()

# 设置中文字体路径（请确保字体文件存在）
# 你可以下载一个中文字体，例如 SimHei，并将其路径设置为 font_path
font_path = '/Users/chauncey/Library/Fonts/MiSans-Normal.ttf'  # 请将此路径替换为你的中文字体路径

# 检查字体文件是否存在
if not os.path.exists(font_path):
    print(f"字体文件 '{font_path}' 不存在。请确保有一个支持中文的字体文件，并将 font_path 设置为正确的路径。")
else:
    # 生成每个主题的词云
    for topic_num in range(num_topics):
        generate_wordcloud(lda_model, topic_num, font_path=font_path)