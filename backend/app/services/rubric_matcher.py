
import re
from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class RubricMatch:
    expected_point: str
    status: str
    evidence: list[str]
    similarity: float


class RubricMatcher:
    """Evidence-based rubric matching using semantic concept aliases."""

    COVERED_THRESHOLD = 0.40
    PARTIAL_THRESHOLD = 0.15

    STOPWORDS = {
        "the", "a", "an", "of", "to", "and", "or", "in",
        "on", "with", "for", "is", "are", "was", "were",
        "by", "from", "into", "that", "this", "it", "its",
        "their", "they", "as", "at", "be", "can", "could",
        "would", "should", "will", "about", "how", "what",
        "when", "where", "which", "who", "then", "also",
        "first", "finally", "after", "before", "such",
        "like", "based", "using", "use", "i", "we", "my",
        "our", "initially", "ultimately",
    }

    CONCEPT_ALIASES = {
        "data preprocessing": {
            "preprocessing", "cleaning", "data cleaning",
            "text cleaning", "normalize", "normalization",
            "lowercase", "stemming", "lemmatization",
            "remove duplicates", "remove noise",
            "missing values", "tokenization",
            "stopword removal", "stop words",
        },
        "feature extraction": {
            "tfidf", "tf idf", "countvectorizer",
            "count vectorizer", "bag of words", "bow",
            "word embeddings", "feature engineering",
            "vectorization", "vectorizer",
            "numerical representation", "text representation",
            "embedding generation",
        },
        "model selection": {
            "logistic regression", "naive bayes", "naivebayes",
            "svm", "support vector machine",
            "random forest", "bert", "distilbert",
            "transformer", "transformers", "classifier",
            "classification model", "baseline model",
            "machine learning model", "deep learning model",
            "fine tuning", "fine-tuning",
        },
        "evaluation metrics": {
            "accuracy", "precision", "recall", "f1",
            "f1 score", "confusion matrix", "roc auc",
            "auc", "evaluation metrics",
            "classification report", "cross validation",
            "validation set", "test set", "metrics",
            "performance evaluation",
        },
        "sentiment classification": {
            "sentiment analysis", "sentiment classification",
            "positive", "negative", "neutral",
            "polarity", "opinion mining",
        },
        "reranking": {
            "reranker", "re ranker", "re-ranking",
            "cross encoder", "cross-encoder",
            "second stage ranking", "relevance ranking",
            "rank retrieved documents",
        },
        "hybrid retrieval": {
            "hybrid search", "bm25", "sparse retrieval",
            "dense retrieval", "dense vector search",
            "reciprocal rank fusion", "rrf",
        },
        "document retrieval": {
            "retrieval", "similarity search",
            "vector search", "semantic search",
            "retrieve relevant documents",
            "retrieved chunks", "top k",
        },
        "relevance scoring": {
            "relevance score", "similarity score",
            "cosine similarity", "relevance ranking",
            "ranking score",
        },
        "rag components": {
            "retriever", "vector database",
            "embedding model", "embeddings",
            "llm", "language model",
            "context", "prompt",
            "knowledge base", "document store",
        },
        "langchain pipeline setup": {
            "langchain", "chain", "retrieval chain",
            "llm chain", "prompt template",
            "orchestration", "pipeline",
        },
        "nlp task implementation": {
            "sentiment analysis", "entity extraction",
            "text classification", "summarization",
            "natural language processing",
        },
        "handling of llm integration": {
            "llm integration", "language model",
            "prompt engineering", "model inference",
            "llm invocation", "generate response",
        },
        "security measures": {
            "authentication", "authorization",
            "rate limiting", "input validation",
            "sanitization", "access control",
            "prompt injection", "secrets management",
        },
        "data integrity checks": {
            "pydantic", "schema validation",
            "type validation", "structured output",
            "response model", "data validation",
            "json validation", "serialization",
        },
        "api integration strategies": {
            "rest api", "rest apis", "http request",
            "requests library", "api integration",
            "endpoint", "api client",
        },
        "data fetching logic": {
            "fetch data", "data ingestion",
            "api call", "get request",
            "pagination", "response parsing",
        },
        "vector database usage": {
            "pinecone", "chroma", "faiss",
            "vector database", "vector store",
            "upsert", "embeddings storage",
            "metadata", "indexing",
        },
        "workflow automation": {
            "airflow", "prefect", "scheduler",
            "orchestration", "automated pipeline",
            "cron", "retry mechanism",
        },
    }

    def _normalize_text(self, text: str) -> str:
        text = text.lower()
        text = text.replace("-", " ")
        text = re.sub(r"[^a-z0-9+#.\s]", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def _normalize_tokens(self, text: str) -> set[str]:
        return {
            token
            for token in self._normalize_text(text).split()
            if token not in self.STOPWORDS and len(token) > 1
        }

    def _extract_sentences(self, text: str) -> list[str]:
        sentences = re.split(r"(?<=[.!?])\s+|[\n]+", text.strip())
        return [sentence.strip() for sentence in sentences if sentence.strip()]

    def _concept_aliases(self, expected_point: str) -> set[str]:
        normalized_point = self._normalize_text(expected_point)
        aliases = set()

        for concept, expressions in self.CONCEPT_ALIASES.items():
            normalized_concept = self._normalize_text(concept)

            if (
                normalized_point == normalized_concept
                or normalized_point in expressions
                or normalized_point in normalized_concept
                or normalized_concept in normalized_point
            ):
                aliases.update(expressions)
                aliases.add(concept)

        return aliases

    def _calculate_keyword_coverage(
        self,
        expected_point: str,
        candidate_answer: str,
    ) -> float:
        expected_tokens = self._normalize_tokens(expected_point)
        answer_tokens = self._normalize_tokens(candidate_answer)

        if not expected_tokens:
            return 0.0

        direct_overlap = len(expected_tokens & answer_tokens)
        direct_coverage = direct_overlap / len(expected_tokens)

        aliases = self._concept_aliases(expected_point)
        normalized_answer = self._normalize_text(candidate_answer)

        if aliases:
            matched_aliases = {
                self._normalize_text(alias)
                for alias in aliases
                if self._normalize_text(alias) in normalized_answer
            }

            # One explicit, distinctive technical alias is meaningful.
            alias_coverage = min(1.0, len(matched_aliases) / 1.0)
            return max(direct_coverage, alias_coverage)

        return direct_coverage

    def _calculate_similarity(
        self,
        expected_point: str,
        candidate_answer: str,
    ) -> float:
        try:
            vectorizer = TfidfVectorizer(
                ngram_range=(1, 2),
                stop_words="english",
            )
            vectors = vectorizer.fit_transform(
                [expected_point, candidate_answer]
            )
            return float(
                cosine_similarity(vectors[0], vectors[1])[0][0]
            )
        except ValueError:
            return 0.0

    def _find_evidence(
        self,
        expected_point: str,
        sentences: list[str],
    ) -> list[str]:
        evidence = []
        expected_tokens = self._normalize_tokens(expected_point)
        aliases = self._concept_aliases(expected_point)

        for sentence in sentences:
            normalized_sentence = self._normalize_text(sentence)
            sentence_tokens = self._normalize_tokens(sentence)

            direct_overlap = expected_tokens & sentence_tokens

            alias_matches = [
                alias
                for alias in aliases
                if self._normalize_text(alias) in normalized_sentence
            ]

            if alias_matches:
                evidence.append(sentence)
                continue

            if len(direct_overlap) >= 2:
                evidence.append(sentence)

        return evidence

    def _determine_status(
        self,
        keyword_coverage: float,
        similarity: float,
        evidence: list[str],
    ) -> str:
        if not evidence:
            return "missing"

        combined_score = max(keyword_coverage, similarity)

        if keyword_coverage >= self.COVERED_THRESHOLD:
            return "covered"

        if combined_score >= self.PARTIAL_THRESHOLD:
            return "partially_covered"

        return "missing"

    def match(
        self,
        expected_points: list[str],
        candidate_answer: str,
    ) -> list[RubricMatch]:
        if not candidate_answer.strip():
            return [
                RubricMatch(
                    expected_point=point,
                    status="missing",
                    evidence=[],
                    similarity=0.0,
                )
                for point in expected_points
            ]

        sentences = self._extract_sentences(candidate_answer)
        results = []

        for point in expected_points:
            keyword_coverage = self._calculate_keyword_coverage(
                point, candidate_answer
            )

            similarity = self._calculate_similarity(
                point, candidate_answer
            )

            evidence = self._find_evidence(point, sentences)

            status = self._determine_status(
                keyword_coverage, similarity, evidence
            )

            combined_score = max(keyword_coverage, similarity)

            results.append(
                RubricMatch(
                    expected_point=point,
                    status=status,
                    evidence=evidence,
                    similarity=round(combined_score, 3),
                )
            )

        return results


rubric_matcher = RubricMatcher()
