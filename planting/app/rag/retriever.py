"""RAG 检索器（轻量本地方案，不依赖外部向量库）。

语料来源两类：
    1. 知识图谱中的 36 条访谈事实（fact 块，带证据编号与口述角色）；
    2. docs/ 目录下的调研 Markdown 文档（doc 块，按段落切块并保留来源标题）。

检索方式：
    对查询与文本分别做 token 化（中文按二元字组、英文数字按整词），
    用 token 交集打分召回 top_k 块；MVP 阶段不引入向量模型，保证离线可跑、结果可解释。

纪律：检索只负责「召回证据」，回答是否合规仍由 Harness 在返回前拦截。
"""

from __future__ import annotations   # 类型注解延迟求值

import re                                   # 正则提取词元与切块
from pathlib import Path                    # 文档路径解析
from typing import Any                     # 标注块字典类型

from app.core.config import PROJECT_ROOT, config   # 读取检索配置与文档目录
from app.core.logger import get_logger              # 统一日志出口
from app.kg.graph import kg                         # 事实语料来自知识图谱单例

logger = get_logger(__name__)   # 绑定本模块日志器

# 词元提取：连续中文片段、英文单词、数字编号分别成组
_TOKEN_PATTERN = re.compile(r"[一-龥]+|[a-zA-Z0-9]+")


def _tokenize(text: str) -> set[str]:
    """把文本切成可比对的词元集合。

    入参：text 任意中文/英文混排文本。
    出参：词元集合；中文片段拆成二元字组，英文与数字整词保留。
    失败行为：空文本返回空集合，不抛异常。
    """
    tokens: set[str] = set()                       # 结果集合，自动去重
    for piece in _TOKEN_PATTERN.findall(text or ""):   # 逐段提取
        if re.fullmatch(r"[一-龥]+", piece):        # 中文片段：拆 bigram，缓解单字匹配噪声
            if len(piece) == 1:                     # 单字直接保留
                tokens.add(piece)
            for i in range(len(piece) - 1):         # 相邻两字成组
                tokens.add(piece[i:i + 2])
        else:                                       # 英文/数字整词入集合
            tokens.add(piece.lower())
    return tokens


def _split_doc_paragraphs(md_text: str, chunk_chars: int) -> list[str]:
    """把 Markdown 文本切成段落块，超长段落再按字符窗口拆分。

    入参：md_text 文档全文；chunk_chars 单块目标字符长度。
    出参：段落文本列表，去掉空白与过短残块。
    失败行为：空文本返回空列表。
    """
    paragraphs: list[str] = []                    # 段落容器
    current: list[str] = []                       # 当前段落累积行
    for line in md_text.splitlines():             # 逐行读取
        stripped = line.strip()
        if not stripped:                          # 空行视为段落分隔
            if current:                           # 段落已有内容才收尾
                paragraphs.append(" ".join(current).strip())
                current = []
            continue
        current.append(stripped)
    if current:                                   # 文末最后一段收尾
        paragraphs.append(" ".join(current).strip())

    chunks: list[str] = []                        # 最终切块容器
    for para in paragraphs:
        if len(para) <= chunk_chars:              # 段落不长，整块保留
            chunks.append(para)
            continue
        # 超长段落按句号/分号切分，再回退到字符窗口
        sentences = re.split(r"(?<=[。；;])", para)
        buf = ""
        for sentence in sentences:
            if len(buf) + len(sentence) > chunk_chars and buf:
                chunks.append(buf.strip())
                buf = sentence
            else:
                buf += sentence
        if buf.strip():
            chunks.append(buf.strip())
    return [c for c in chunks if len(c) >= 8]     # 过滤过短残块，避免噪声命中


class Retriever:
    """检索器门面：启动时构建语料索引，请求时打分召回。"""

    def __init__(self) -> None:
        """初始化空索引，真正构建由 build() 触发。"""
        self._chunks: list[dict[str, Any]] = []   # 全部语料块（含词元集合）
        self._built = False                       # 索引是否已构建

    def _fact_chunks(self) -> list[dict[str, Any]]:
        """从知识图谱取出 36 条事实作为 fact 语料块。

        入参：无。
        出参：事实块列表，每块含 kind/source/evidence_id/role/text/tokens。
        失败行为：图谱未加载时先触发 load()。
        """
        if kg.graph.number_of_nodes() == 0:       # 空库先加载，避免取不到事实
            kg.load()
        chunks: list[dict[str, Any]] = []
        for _, attr in kg.graph.nodes(data=True):   # 遍历图谱节点
            if attr.get("node_type") != "fact":     # 只取事实节点
                continue
            text = attr.get("text", "")
            chunks.append({
                "kind": "fact",
                "source": "访谈记录",
                "evidence_id": attr.get("evidence_id", ""),
                "role": attr.get("role", ""),
                "category": attr.get("category", ""),
                "title": f"{attr.get('evidence_id', '')} · {attr.get('role', '')}",
                "text": text,
                "tokens": _tokenize(text + attr.get("role", "")),
            })
        return chunks

    def _doc_chunks(self) -> list[dict[str, Any]]:
        """扫描 docs 目录下的 Markdown 文档并切块。

        入参：无。
        出参：doc 块列表；读取失败的文档跳过并记日志，不中断启动。
        失败行为：目录不存在时返回空列表。
        """
        docs_dir = Path(config.rag.docs_dir)
        if not docs_dir.is_absolute():            # 相对路径一律相对项目根
            docs_dir = (PROJECT_ROOT / docs_dir).resolve()
        if not docs_dir.exists():                 # 目录缺失不阻断服务
            logger.warning("文档目录不存在，跳过文档切块：%s", docs_dir)
            return []

        chunks: list[dict[str, Any]] = []
        for md_file in sorted(docs_dir.glob("*.md")):   # 仅收录 md，docx 不参与文本检索
            try:
                text = md_file.read_text(encoding="utf-8")
            except OSError as exc:                # 单文件失败不影响其他文档
                logger.warning("读取文档失败 %s：%s", md_file.name, exc)
                continue
            for para in _split_doc_paragraphs(text, config.rag.doc_chunk_chars):
                chunks.append({
                    "kind": "doc",
                    "source": md_file.name,
                    "evidence_id": "",
                    "role": "",
                    "title": md_file.stem,
                    "text": para,
                    "tokens": _tokenize(para),
                })
        return chunks

    def build(self) -> None:
        """构建全量检索索引（事实块 + 文档块）。

        入参：无。
        出参：无（原地填充 self._chunks）。
        失败行为：单类语料异常不吞掉构建结果，日志记录后继续。
        """
        chunks = self._fact_chunks()               # 先收事实块
        chunks.extend(self._doc_chunks())          # 再拼文档块
        self._chunks = chunks
        self._built = True
        logger.info("RAG 索引构建完成：%d 个语料块", len(chunks))

    def _score(self, query_tokens: set[str], chunk_tokens: set[str]) -> float:
        """计算查询与语料块的匹配得分。

        入参：query_tokens 查询词元；chunk_tokens 语料块词元。
        出参：浮点得分，交集词元数按双方长度做归一化，避免长文本天然占优。
        失败行为：任一集合为空返回 0。
        """
        if not query_tokens or not chunk_tokens:
            return 0.0
        overlap = len(query_tokens & chunk_tokens)
        if overlap == 0:
            return 0.0
        # 简化余弦：交集 / sqrt(|A|*|B|)，词元重叠越多得分越高
        return overlap / (len(query_tokens) * len(chunk_tokens)) ** 0.5

    def retrieve(self, query: str, top_k: int | None = None) -> list[dict[str, Any]]:
        """按查询召回最相关的语料块。

        入参：
            query 用户问题；top_k 返回条数上限，缺省取配置 rag.top_k。
        出参：块列表（去掉内部 tokens 字段），按得分降序；无命中返回空列表。
        失败行为：查询为空返回空列表；索引未构建时先自动 build()。
        """
        if not query or not query.strip():
            return []
        if not self._built:                        # 兜底：未构建则现场构建
            self.build()

        limit = top_k or config.rag.top_k
        query_tokens = _tokenize(query)
        scored: list[tuple[float, dict[str, Any]]] = []
        for chunk in self._chunks:
            score = self._score(query_tokens, chunk["tokens"])
            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda item: item[0], reverse=True)   # 高分在前
        result: list[dict[str, Any]] = []
        for score, chunk in scored[:limit]:
            public = {k: v for k, v in chunk.items() if k != "tokens"}   # 不把内部词元外泄
            public["score"] = round(score, 4)
            result.append(public)
        return result

    def stats(self) -> dict[str, Any]:
        """返回索引规模统计，供 /health 与前端展示。

        入参：无。
        出参：总块数、事实块数、文档块数。
        失败行为：未构建时返回零值统计。
        """
        fact_count = sum(1 for c in self._chunks if c["kind"] == "fact")
        return {
            "chunks": len(self._chunks),
            "facts": fact_count,
            "docs": len(self._chunks) - fact_count,
        }


# 进程内单例，供路由与问答服务复用
retriever = Retriever()
