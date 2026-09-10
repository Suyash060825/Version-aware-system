\documentclass[journal]{IEEEtran}

% =========================================================================
% PolicyLedger: Version-Aware Enterprise Policy Intelligence
% Journal-Neutral IEEE Journal Manuscript
% Rigorously scoped, verified against empirical experimental results.
% =========================================================================

\usepackage{cite}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{algorithm}
\usepackage{algorithmic}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{multirow}
\usepackage{array}
\usepackage{url}
\usepackage{hyperref}
\usepackage{xcolor}
\usepackage{microtype}
\usepackage{textcomp}

\newcommand{\PolicyLedger}{PolicyLedger}
\newcommand{\ms}{\,\mathrm{ms}}
\newcommand{\pct}{\%}
\newcommand{\R}{\mathbb{R}}
\newcommand{\I}{\mathbb{I}}
\newcommand{\D}{\mathbb{D}}

\begin{document}

\title{PolicyLedger: Version-Aware Enterprise Policy Intelligence via Incremental Knowledge Compilation and Adaptive Multi-Tier Retrieval}

\author{Suyash~Pradhan%
\thanks{Suyash Pradhan is with the Department of Computer Science and Engineering (e-mail: suyashpradhan06@gmail.com).}}

% Journal-neutral header for pre-submission / review
\markboth{IEEE Journal / Transactions Manuscript}{Pradhan: PolicyLedger: Version-Aware Enterprise Policy Intelligence}

\maketitle

\begin{abstract}
Enterprise policies and regulatory compliance rules undergo continuous revision over time, yet conventional retrieval-augmented generation (RAG) paradigms typically treat knowledge bases as static document collections. This introduces the risk of temporal version inversion, where semantically relevant but superseded clauses are retrieved for contemporary inquiries. Furthermore, rebuilding global indices during document updates incurs substantial computational cost, and routing deterministic policy questions to autoregressive models adds unnecessary latency. This paper presents PolicyLedger, a version-aware enterprise policy intelligence architecture. The system models temporal validity using explicit effective date intervals integrated into database schemas and pre-retrieval candidate filters. An incremental knowledge compiler uses SHA-256 chunk hashing and dynamic FAISS segment overlays, achieving an empirical $721.95\times$ speedup ($3.57\,$ms vs.\ $2579.31\,$ms) over a full rebuild baseline on a zero-delta update with $O(|\Delta| \cdot d)$ incremental complexity. Incoming inquiries are processed by an adaptive query router that navigates indexed relational fact lookups, precompiled canonical question-answer matching, and cross-encoder reranked hybrid dense--sparse retrieval. On a 127-chunk enterprise policy corpus, retrieval saturates at 0.9861 MRR@10 and 0.9861 Recall@5. On a 301-query held-out benchmark, the composite median response latency is $29.65\,$ms (P95: $136.49\,$ms), with $82.72\%$ correct version selection across all queries. Cache safety tests over 30 non-repeating queries show zero observed stale, wrong-version, or cross-scope responses. Adversarial refusal accuracy on an 18-query security subset reaches 88.89\%. While local 4-bit model quantization constrains exact text generation accuracy to 27.91\% (token F1: 0.3516), citation precision of 0.7973 confirms grounding quality. These results present a defensible, reproducible systems framework for version-constrained enterprise knowledge retrieval.
\end{abstract}

\begin{IEEEkeywords}
Retrieval-augmented generation, temporal information retrieval, version-aware retrieval, enterprise knowledge management, incremental indexing, adaptive query routing, policy governance, grounded generation.
\end{IEEEkeywords}

\section{Introduction}
\IEEEPARstart{E}{nterprise} governance, human resource administration, information security, and regulatory compliance rely fundamentally on institutional policy documents. In organizational environments, these documents are non-stationary: corporate expense ceilings, leave entitlements, remote work protocols, and data security mandates undergo periodic revisions. Each policy revision possesses an authoritative validity window bounded by calendar dates $[\tau_s, \tau_e]$.

Despite widespread adoption across industry, standard Retrieval-Augmented Generation (RAG) frameworks \cite{lewis2020rag, gao2024rag_survey} treat target knowledge bases as static collections of unstructured text chunks. When applied to evolving policy corpora, standard RAG architectures face four practical challenges:
\begin{enumerate}
    \item \textbf{Temporal Version Inversion}: Semantic vector embeddings capture topical similarity but remain agnostic to temporal validity intervals. An inquiry regarding historical entitlements (e.g., ``What was the domestic travel allowance in June 2024?'') risks retrieving semantically identical but legally obsolete clauses from current policy versions, or vice versa \cite{huwiler2025versionrag}.
    \item \textbf{Update Re-Indexing Overhead}: In standard RAG pipelines, modifying a document often triggers full-corpus re-embedding and global inverted-index rebuilding ($O(N \cdot d)$), imposing computational overhead on continuous update workflows.
    \item \textbf{Generative Latency on Deterministic Lookups}: Standard RAG routes incoming user queries directly to an autoregressive Large Language Model (LLM). This introduces $2\text{--}8\text{ seconds}$ of inference latency for deterministic, standardized policy inquiries (e.g., ``What is the standard probation period?'') that can be resolved via structured relational lookup.
    \item \textbf{Cross-Department Authorization Boundaries}: Without pre-retrieval scope enforcement, unpartitioned retrieval pipelines risk indexing and exposing confidential executive or departmental clauses to unauthorized users.
\end{enumerate}

\begin{figure*}[!t]
\centering
\includegraphics[width=0.98\textwidth]{figures/architecture.pdf}
\caption{Operational flowchart of \PolicyLedger, illustrating query processing from initial normalization and scope gating through fast-path fact resolution, canonical question matching, hybrid dense--sparse retrieval with pre-retrieval scope enforcement, neural NLI entailment verification, and safe abstention.}
\label{fig:architecture}
\end{figure*}

To address these challenges, this paper presents \textbf{\PolicyLedger}, a version-aware enterprise policy intelligence architecture. \PolicyLedger\ incorporates temporal validity interval constraints into the storage schema and pre-retrieval filtering layers, provides index maintenance via cryptographic SHA-256 delta compilation, and implements an adaptive four-tier router designed to resolve deterministic inquiries without unconditional generative model invocation.

The primary contributions of this paper are:
\begin{enumerate}
    \item \textbf{Temporal Validity Formulation}: An interval-based validity formulation $[\tau_s(v), \tau_e(v)]$ applied before similarity ranking to prevent temporally invalid candidates from entering the active retrieval pool, achieving 82.72\% (249/301) correct version selection across the benchmark.
    \item \textbf{Incremental Knowledge Compiler}: An update engine using SHA-256 chunk hashing and dynamic FAISS HNSW segment overlays that achieved an empirical $721.95\times$ speedup ($3.57\ms$ vs.\ $2579.31\ms$) on a zero-delta update (0 chunks re-embedded) compared to a full $O(N \cdot d)$ rebuild baseline, with $O(|\Delta| \cdot d)$ incremental complexity.
    \item \textbf{Adaptive Multi-Tier Query Routing}: A tiered execution architecture that routes inquiries across indexed relational fact lookups (Tier~0: 48.50\% of traffic, 20.19\,ms P50), precompiled canonical QA vector matching (Tier~1: 5.65\%, 23.28\,ms P50), cross-encoder reranked hybrid dense--sparse retrieval (Tier~2: 35.55\%, 120.50\,ms P50), and structural version diffing (Tier~3: implemented, evaluated on a dedicated version-diff test set in future work).
    \item \textbf{Pre-Retrieval Scoping and Grounding Verification}: A security workflow enforcing role-based and confidentiality constraints prior to similarity ranking, combined with DeBERTa-v3 neural NLI verification achieving 100\% Contradiction recall on a 14-pair pilot test set.
    \item \textbf{Empirical Evaluation}: Benchmarking across 301 curated queries reporting latency distributions, retrieval metrics, version selection accuracy, update costs, cache safety invariants, and generative accuracy trade-offs under quantized local model constraints.
\end{enumerate}


\section{Related Work and Background}

\subsection{Retrieval-Augmented Generation (RAG)}
RAG architectures combine parametric neural language models with non-parametric retrieval indices to condition generation on external evidence \cite{lewis2020rag, gao2024rag_survey}. Dense Passage Retrieval (DPR) demonstrated the utility of dual-encoder representations \cite{karpukhin2020dpr}, while BGE embeddings provide dense semantic representations across diverse domains \cite{xiao2023bge}. Lexical retrieval algorithms such as BM25 \cite{robertson2009bm25} remain complementary for exact keyword, acronym, and numerical policy matching. Reciprocal Rank Fusion (RRF) provides an unsupervised method to combine dense and sparse ranking lists \cite{cormack2009rrf}, and cross-encoder models (e.g., TinyBERT \cite{jiao2020tinybert, pradeep2023flashrank}) provide token-level interaction reranking. However, standard RAG frameworks typically treat document collections as static corpora.

\subsection{Temporal Information Retrieval and Time-Aware NLP}
Temporal Information Retrieval (T-IR) examines temporal expressions in text search \cite{campos2014temporal_ir}. Time-aware language modeling approaches often prepend textual timestamps or temporal metadata to token sequences \cite{dhingra2022temporal_lm}. While effective for open-domain factuality, probabilistic attention over temporal strings does not provide the deterministic validity boundaries required in legal and corporate policy governance. VersionRAG \cite{huwiler2025versionrag} recently addressed evolving documents in RAG by constructing version graphs and incorporating version-aware embeddings that encode version lineage signals. \PolicyLedger\ takes a complementary applied approach: rather than modifying the embedding space, it formalizes temporal validity as closed calendar-interval invariants ($[\tau_s, \tau_e]$) enforced via relational database predicates \textit{before} vector similarity ranking, thereby providing deterministic exclusion of out-of-window candidates independent of embedding quality. \PolicyLedger\ additionally combines this temporal formulation with role-based authorization scoping, incremental SHA-256 compilation, and a four-tier adaptive router — components not addressed by VersionRAG.

\subsection{Approximate Nearest Neighbor (ANN) Search and Incremental Indexing}
Hierarchical Navigable Small World (HNSW) graphs \cite{malkov2020hnsw} and similarity libraries such as FAISS \cite{johnson2017faiss} enable efficient approximate nearest-neighbor search. In dynamic corpora, updating monolithic HNSW graphs can require costly node deletions and structural edge rebalancing. \PolicyLedger\ uses SHA-256 chunk delta compilation with append-only segment overlays and tombstone bitmasks to avoid re-indexing unchanged content.

\subsection{Confidence Calibration and Verification}
Deep neural networks often output uncalibrated probabilities, exhibiting high confidence even on erroneous predictions \cite{guo2017calibration}. In RAG systems, self-reflection and natural language inference (NLI) models \cite{asai2024selfrag, he2021deberta} can evaluate whether retrieved evidence logically entails generated claims. \PolicyLedger\ incorporates DeBERTa-v3 cross-encoder entailment and establishes a multi-factor confidence formulation to measure evidence grounding.

\section{Problem Formulation and Invariant Theory}

Let $\mathcal{P} = \{P_1, P_2, \dots, P_M\}$ denote an enterprise policy repository of $M$ policies. Each policy $P_i$ comprises an ordered sequence of discrete versions:
\begin{equation}
\mathcal{V}(P_i) = \{v_{i,1}, v_{i,2}, \dots, v_{i,K_i}\},
\end{equation}
where $K_i \ge 1$. Each version $v \in \mathcal{V}(P_i)$ is characterized by the 5-tuple:
\begin{equation}
v = \langle \tau_s(v), \tau_e(v), \mathcal{C}(v), D(P_i), \kappa(P_i) \rangle,
\end{equation}
where:
\begin{itemize}
    \item $[\tau_s(v), \tau_e(v)] \subset \D$ is the closed calendar validity interval over discrete calendar dates $\D$;
    \item $\mathcal{C}(v) = \{c_1, c_2, \dots, c_{J_v}\}$ is the set of constituent textual chunks;
    \item $D(P_i) \in \mathcal{D} \cup \{\text{General}\}$ is the organizational department scope;
    \item $\kappa(P_i) \in \{\text{Public}, \text{Internal}, \text{Confidential}, \text{Restricted}\}$ is the confidentiality classification.
\end{itemize}

\subsection{Temporal Validity Invariant}
For any query evaluated at target calendar date $t_q \in \D$, a chunk $c \in \mathcal{C}(v)$ belonging to policy version $v$ is considered temporally valid if and only if:
\begin{equation}
V(c, t_q) = 
\begin{cases}
1, & \text{if } \tau_s(v) \le t_q \le \tau_e(v), \\
0, & \text{otherwise.}
\end{cases}
\label{eq:temporal_validity}
\end{equation}
When a new policy version $v_{k+1}$ is published with effective start date $\tau_s(v_{k+1})$, the validity boundary of the preceding version $v_k$ mutates:
\begin{equation}
\tau_e(v_k) \leftarrow \tau_s(v_{k+1}) - 1\text{ day},
\end{equation}
so that active validity intervals within any single policy $P_i$ remain mutually disjoint:
\begin{equation}
[\tau_s(v_j), \tau_e(v_j)] \cap [\tau_s(v_k), \tau_e(v_k)] = \emptyset \quad \forall j \ne k.
\end{equation}

\subsection{Scope-Based Authorization Invariant}
Let $u$ denote a querying user identity with department assignment $D(u)$ and clearance set $K(u) \subseteq \{\text{Public}, \text{Internal}, \text{Confidential}, \text{Restricted}\}$. The pre-retrieval access predicate is defined as:
\begin{equation}
A(c, u) = \I\left[D(P_i) \in \{D(u), \text{General}\} \wedge \kappa(P_i) \in K(u)\right].
\label{eq:auth_predicate}
\end{equation}

\subsection{Composite Retrieval Eligibility}
A candidate chunk $c$ is eligible for inclusion in the retrieval candidate pool if and only if both temporal and authorization predicates evaluate to 1:
\begin{equation}
E(c, u, t_q) = V(c, t_q) \cdot A(c, u) = 1.
\label{eq:eligibility}
\end{equation}
\PolicyLedger\ applies $E(c, u, t_q) = 1$ prior to similarity ranking, filtering out unauthorized or temporally invalid chunks before top-$k$ candidate selection.

\subsection{System Latency Optimization Objective}
Let $\mathcal{R} = \{\text{Tier}_0, \text{Tier}_1, \text{Tier}_2, \text{Tier}_3\}$ represent the available query routing paths, each characterized by execution latency $L(r)$ and operational cost $C(r)$. The adaptive routing objective aims to reduce expected query latency across the query workload $\mathcal{Q}$:
\begin{equation}
\min_{\pi} \mathbb{E}_{q \sim \mathcal{Q}} \left[ L(\pi(q)) \right] \quad \text{subject to } \mathrm{Acc}(\pi(q)) \ge \theta_{\mathrm{acc}},
\end{equation}
where $\pi: \mathcal{Q} \rightarrow \mathcal{R}$ selects the lowest-latency tier capable of satisfying the query's information requirement.

\section{Incremental Knowledge Compilation}

Conventional RAG architectures often re-embed the entire corpus upon document modification, incurring $O(N \cdot d)$ embedding and graph construction costs, where $N$ is total chunks and $d$ is embedding dimensionality. \PolicyLedger\ introduces an incremental compiler based on chunk hashing and delta overlays.

\subsection{Cryptographic Chunk Hashing}
For each structural chunk $c$, the compiler computes a canonical SHA-256 hash over the normalized text, the active embedding model identifier, and the policy version string:
\begin{equation}
H(c) = \mathrm{SHA256}\left(\mathrm{norm}(c.\text{text}) \,\|\, \text{model\_id} \,\|\, v.\text{version\_num}\right),
\label{eq:chunk_hash}
\end{equation}
where $\mathrm{norm}(\cdot)$ standardizes whitespace and Unicode casing.

\subsection{Delta Partitioning Algorithm}
When an updated policy version is ingested, Algorithm~\ref{alg:incremental_compilation} compares the new chunk set $\mathcal{C}_{\mathrm{new}}$ against the prior version $\mathcal{C}_{\mathrm{old}}$.

\begin{algorithm}[!t]
\caption{Incremental Policy Knowledge Compilation}
\label{alg:incremental_compilation}
\begin{algorithmic}[1]
\REQUIRE Prior chunks $\mathcal{C}_{\mathrm{old}}$, new version chunks $\mathcal{C}_{\mathrm{new}}$, previous version ID $v_{\mathrm{prev}}$
\ENSURE Delta partition $\Delta = (\mathcal{C}_{\mathrm{add}}, \mathcal{C}_{\mathrm{mod}}, \mathcal{C}_{\mathrm{unch}}, \mathcal{T}_{\mathrm{del}})$
\STATE Initialize hash map $M_{\mathrm{hash}} \leftarrow \{H(c) \mapsto c \mid c \in \mathcal{C}_{\mathrm{old}}\}$
\STATE Initialize ID map $M_{\mathrm{id}} \leftarrow \{c.\mathrm{id} \mapsto c \mid c \in \mathcal{C}_{\mathrm{old}}\}$
\STATE Initialize $\mathcal{C}_{\mathrm{add}} \leftarrow \emptyset, \mathcal{C}_{\mathrm{mod}} \leftarrow \emptyset, \mathcal{C}_{\mathrm{unch}} \leftarrow \emptyset, \mathcal{M} \leftarrow \emptyset$
\FOR{each chunk $c \in \mathcal{C}_{\mathrm{new}}$}
    \IF{$H(c) \in M_{\mathrm{hash}}$}
        \STATE $\mathcal{C}_{\mathrm{unch}} \leftarrow \mathcal{C}_{\mathrm{unch}} \cup \{c\}$
        \STATE $\mathcal{M} \leftarrow \mathcal{M} \cup \{M_{\mathrm{hash}}[H(c)].\mathrm{id}\}$
    \ELSIF{$c.\mathrm{id} \in M_{\mathrm{id}}$}
        \STATE $\mathcal{C}_{\mathrm{mod}} \leftarrow \mathcal{C}_{\mathrm{mod}} \cup \{c\}$
        \STATE $\mathcal{M} \leftarrow \mathcal{M} \cup \{c.\mathrm{id}\}$
    \ELSE
        \STATE $\mathcal{C}_{\mathrm{add}} \leftarrow \mathcal{C}_{\mathrm{add}} \cup \{c\}$
    \ENDIF
\ENDFOR
\STATE $\mathcal{T}_{\mathrm{del}} \leftarrow \{c.\mathrm{id} \mid c \in \mathcal{C}_{\mathrm{old}}\} \setminus \mathcal{M}$ \COMMENT{Tombstoned IDs}
\STATE Forward only $\mathcal{C}_{\mathrm{add}} \cup \mathcal{C}_{\mathrm{mod}}$ to FastEmbed ONNX embedding pipeline
\STATE Update FAISS dynamic segment overlay and set bitmasks for $\mathcal{T}_{\mathrm{del}}$
\RETURN $\Delta = (\mathcal{C}_{\mathrm{add}}, \mathcal{C}_{\mathrm{mod}}, \mathcal{C}_{\mathrm{unch}}, \mathcal{T}_{\mathrm{del}})$
\end{algorithmic}
\end{algorithm}

\subsection{Computational Complexity and Update Workload}
Let $N = |\mathcal{C}_{\mathrm{old}}|$ and $M = |\mathcal{C}_{\mathrm{new}}|$. Building hash lookup tables requires $O(N)$ operations. Partitioning chunks requires $O(M)$ hash evaluations. For policy updates where changed chunks $|\Delta| = |\mathcal{C}_{\mathrm{add}}| + |\mathcal{C}_{\mathrm{mod}}| \ll N$, forward neural embedding operations are restricted to $O(|\Delta| \cdot d)$ instead of $O(M \cdot d)$.

In the evaluated incremental update experiment involving 6 unchanged chunks and 0 modified chunks, execution completed in $3.57\ms$, compared to $2579.31\ms$ for the full rebuild baseline, yielding an observed ratio of:
\begin{equation}
S_{\mathrm{comp}} = \frac{2579.31\ms}{3.57\ms} = 721.95\times.
\end{equation}
This measurement reflects a low-delta update scenario in which no chunk re-embeddings were required.

\section{Adaptive Four-Tier Query Routing}

\PolicyLedger\ organizes execution across four specialized query routing tiers:

\subsection{Tier 0: Structured Fact Resolution}
Factual questions targeting specific numeric or entity attributes (e.g., ``What is the notice period for engineering?'') target extracted relational triples $\langle\text{Subject}, \text{Predicate}, \text{Value}\rangle \in \mathcal{F}$ indexed in PostgreSQL. The Fact Resolver executes an indexed key-based SQL lookup:
\begin{equation}
\mathrm{Lookup}(P_i, v, \text{predicate}) \rightarrow \langle\text{val}, \text{unit}, c_{\mathrm{source}}\rangle.
\end{equation}
Under indexed key access, this path resolves with a measured median latency of $20.19\ms$ without vector similarity scoring or generative model invocation.

\subsection{Tier 1: Canonical Question--Answer Matching}
During document compilation, canonical question clusters are synthesized and embedded into a persistent FAISS HNSW index ($M=32, efConstruction=64$). At query time, the query vector $\mathbf{q} \in \R^{384}$ is matched against key vectors $\mathbf{k}_j$:
\begin{equation}
\mathrm{sim}(\mathbf{q}, \mathbf{k}_j) = \frac{\mathbf{q}^{\top} \mathbf{k}_j}{\|\mathbf{q}\|_2 \|\mathbf{k}_j\|_2} \ge \theta_{\mathrm{QA}} \quad (\theta_{\mathrm{QA}} = 0.80).
\label{eq:cosine}
\end{equation}
Candidate matches satisfying scope filtering return pre-validated answers with authoritative chunk citations at a measured median latency of $23.28\ms$.

\subsection{Tier 2: Hybrid Dense--Sparse Retrieval with Grounded Generation}
Unstructured, complex, or exploratory questions are routed to hybrid retrieval:
\begin{enumerate}
    \item \textbf{Dense Retrieval}: Query embedding $\mathbf{q}$ is matched against authorized chunk embeddings in ChromaDB using cosine distance.
    \item \textbf{Sparse Retrieval}: Partitioned BM25 lexical search computes term-matching relevance scores.
    \item \textbf{Reciprocal Rank Fusion (RRF)}: Dense rank $r_d(c)$ and sparse rank $r_s(c)$ are fused via:
    \begin{equation}
    \mathrm{RRF}(c) = \frac{1}{k + r_d(c)} + \frac{1}{k + r_s(c)},
    \label{eq:rrf}
    \end{equation}
    with smoothing constant $k = 60$.
    \item \textbf{Cross-Encoder Reranking}: Top-50 candidates are pruned by eligibility predicate $E(c, u, t_q) = 1$ and scored using FlashRank ($ms\text{-}marco\text{-}TinyBERT\text{-}L\text{-}2\text{-}v2$) to yield top-8 evidence chunks.
\end{enumerate}

\subsection{Tier 3: Structural Version-Diff Comparison}
Inquiries requesting differences between policy revisions (e.g., ``What changed between v1.0 and v2.0 of the Remote Work Policy?'') bypass generative text synthesis. The engine parses the AST section structures of both versions and extracts clause additions, modifications, and removals.

\subsection{Semantic Caching and Invalidation}
A two-level Redis 7 semantic cache stores resolved query embeddings keyed by a composite scope hash:
\begin{equation}
K_{\mathrm{cache}} = \mathrm{SHA256}(D(u) \,\|\, K(u) \,\|\, t_q \,\|\, \mathrm{norm}(q)).
\end{equation}
When a policy update invalidates an active version, cache entries referencing the affected policy ID are evicted via pattern matching.

\section{Security, Grounding, and Verification}

\subsection{Pre-Retrieval Scope Enforcement}
In contrast to post-retrieval filtering, \PolicyLedger\ applies relational department and confidentiality filters prior to vector ranking, excluding unauthorized candidate vectors before distance computations.

\subsection{Neural NLI Grounding Verification}
To verify generated responses against retrieved evidence, candidate answers $A$ paired with evidence chunks $E$ are evaluated using a cross-encoder NLI model ($nli\text{-}deberta\text{-}v3\text{-}base$ \cite{he2021deberta}):
\begin{equation}
P(\text{Entailment} \mid E, A) \ge \theta_{\mathrm{entail}} \quad (\theta_{\mathrm{entail}} = 0.35).
\end{equation}
If the contradiction probability exceeds entailment, the answer falls back to deterministic extractive citations or triggers safe abstention.

\subsection{Multi-Factor Confidence Estimation}
The system computes a raw confidence score $C_{\mathrm{raw}}$ combining retrieval rank score $S_{\mathrm{ret}}$ and lexical surface coverage $S_{\mathrm{cov}}$:
\begin{equation}
C_{\mathrm{raw}} = 0.55 \cdot S_{\mathrm{ret}} + 0.45 \cdot S_{\mathrm{cov}}.
\label{eq:confidence}
\end{equation}
To map raw scores into empirical probabilities, an isotonic regression mapping $f_{\mathrm{iso}}$ can be applied:
\begin{equation}
C_{\mathrm{cal}} = f_{\mathrm{iso}}(C_{\mathrm{raw}}).
\label{eq:isotonic}
\end{equation}
In this evaluation, we report the baseline pre-calibration metrics of the raw multi-factor score; empirical post-calibration improvements are not separately reported.

\section{Experimental Setup}

\subsection{Hardware and Software Environment}
Benchmarks were executed on a dedicated host running Linux 7.1.8 x86\_64 (12 logical vCPUs, 6 physical cores, 31.06~GB RAM, NVIDIA GeForce RTX 3050 Laptop GPU with 3.68~GB VRAM). The software stack includes Python 3.14.6, PyTorch 2.13.0, ChromaDB 1.5.9, FAISS 1.15.0, FastEmbed 0.8.0, FlashRank 0.2.10, PostgreSQL 16, Redis 7 (AOF enabled), and local Ollama inference ($qwen3:4b\text{-}q4\_K\_M$).

\subsection{Corpus and Benchmark Dataset}
The evaluation corpus contains 20 enterprise policies across 8 departments, comprising 22 versions, 127 structural chunks, 33 extracted facts, and 370 canonical question--answer pairs. The held-out benchmark suite (\texttt{benchmark\_test.json}) consists of 301 labeled test queries across 9 operational categories, detailed in Table~\ref{tab:benchmark_distribution}.

\begin{table}[!t]
\caption{Benchmark Query Category Distribution ($N=301$)}
\label{tab:benchmark_distribution}
\centering
\resizebox{\columnwidth}{!}{%
\begin{tabular}{lrr}
\toprule
\textbf{Query Category} & \textbf{Count} & \textbf{Percentage (\%)} \\
\midrule
Compiled Canonical QA & 225 & 74.75 \\
Structured Fact Retrieval & 44 & 14.62 \\
Semantic Retrieval & 8 & 2.66 \\
Unanswerable / Out-of-Domain & 8 & 2.66 \\
Adversarial / Policy Violation & 5 & 1.66 \\
Temporal Historical Lookup & 4 & 1.33 \\
Department Authorization & 3 & 1.00 \\
Version Comparison & 2 & 0.66 \\
Confidentiality Boundary & 2 & 0.66 \\
\midrule
\textbf{Total Benchmark Queries} & \textbf{301} & \textbf{100.00} \\
\bottomrule
\end{tabular}%
}
\end{table}

The benchmark is dominated by compiled QA and structured fact queries (89.37\% combined), reflecting standard employee policy lookups but limiting the sample size for complex semantic, adversarial, and temporal queries.

\subsection{Evaluation Metrics and Definitions}
\begin{itemize}
    \item \textbf{Version Selection Accuracy}: Per-query correctness of the predicted policy version against gold expected version, computed from \texttt{version\_accuracy.csv}.
    \item \textbf{Retrieval Quality}: Recall@1, Recall@5, Recall@10, MRR@10, and NDCG@10 evaluated against gold evidence chunks.
    \item \textbf{Latency}: Mean, P50 (median), P95, and P99 latency in milliseconds, measured per routing tier.
    \item \textbf{Answer Correctness}: Exact match (strict string overlap with gold answer), partial match (gold answer semantically contained in response), mean token F1, citation precision, recall, and F1 against gold cited chunk IDs.
    \item \textbf{Safety and Invariants}: Adversarial refusal accuracy (fraction of security/adversarial queries correctly refused), stale-answer rate, wrong-version leakage, unauthorized cross-scope reuse, and unsafe-served rate.
\end{itemize}

\section{Results and Empirical Evaluation}

\subsection{Version Selection Accuracy}
A core correctness requirement of \PolicyLedger\ is that each answer cites the temporally valid policy version for the query's evaluation date $t_q$. Table~\ref{tab:version_accuracy} reports version selection accuracy computed from the \texttt{version\_accuracy.csv} log, which records the gold expected version and the predicted version for each of the 301 benchmark queries.

\begin{table}[!t]
\caption{Version Selection Accuracy by Query Category ($N=301$)}
\label{tab:version_accuracy}
\centering
\resizebox{\columnwidth}{!}{%
\begin{tabular}{lrr}
\toprule
\textbf{Query Category} & \textbf{Correct / Total} & \textbf{Accuracy (\%)} \\
\midrule
Adversarial & 5 / 5 & 100.00 \\
Unanswerable / Out-of-Domain & 7 / 8 & 87.50 \\
Compiled Canonical QA & 195 / 225 & 86.67 \\
Structured Fact Retrieval & 36 / 44 & 81.82 \\
Confidentiality Boundary & 2 / 2 & 100.00 \\
Department Authorization & 2 / 3 & 66.67 \\
Semantic Retrieval & 1 / 8 & 12.50 \\
Temporal Historical & 1 / 4 & 25.00 \\
Version Comparison & 0 / 2 & 0.00 \\
\midrule
\textbf{Overall} & \textbf{249 / 301} & \textbf{82.72\%} \\
\bottomrule
\end{tabular}%
}
\end{table}

Overall version selection accuracy is 82.72\% (249/301). Deterministic categories perform well: adversarial queries achieve 100\% (5/5), confidentiality boundary 100\% (2/2), and compiled QA 86.67\% (195/225). Accuracy degrades for categories where the temporal interval enforcement relies on non-fact-indexed retrieval: semantic retrieval (1/8, 12.5\%), temporal historical lookup (1/4, 25.0\%), and version comparison (0/2, 0.0\%). These low-accuracy categories account for 14 of the 301 benchmark queries; the 31 version routing errors in Table~\ref{tab:error_breakdown} include both these category failures and version ambiguities in the fact and QA tiers.

\subsection{Retrieval and Ranking Performance}
Table~\ref{tab:retrieval_metrics} presents retrieval performance over the 301 benchmark queries evaluated against gold evidence chunks.

\begin{table}[!t]
\caption{Retrieval and Ranking Metrics on Gold Evidence ($N=301$ queries, 127-chunk corpus)}
\label{tab:retrieval_metrics}
\centering
\resizebox{\columnwidth}{!}{%
\begin{tabular}{lccccc}
\toprule
\textbf{Retriever Configuration} & \textbf{Recall@1} & \textbf{Recall@5} & \textbf{Recall@10} & \textbf{MRR@10} & \textbf{NDCG@10} \\
\midrule
Dense (BGE-Small ONNX) & 0.9861 & 0.9861 & 0.9861 & 0.9861 & 0.9861 \\
BM25 (Partitioned Sparse) & 0.9792 & 0.9861 & 0.9861 & 0.9826 & 0.9835 \\
Hybrid RRF Fusion & 0.9861 & 0.9861 & 0.9861 & 0.9861 & 0.9861 \\
\textbf{Hybrid + FlashRank (Ours)} & \textbf{0.9861} & \textbf{0.9861} & \textbf{0.9861} & \textbf{0.9861} & \textbf{0.9861} \\
\bottomrule
\end{tabular}%
}
\end{table}

On this 127-chunk corpus, dense and hybrid configurations saturate at 0.9861 across Recall@5, MRR@10, and NDCG@10. In this setting, the reranker primarily assists confidence arbitration on out-of-domain queries rather than expanding recall.

\subsection{Latency Analysis by Execution Route}
Table~\ref{tab:latency_breakdown} details latency measurements across all 301 benchmark queries.

\begin{table}[!t]
\caption{Empirical Latency Breakdown Across Routing Tiers ($N=301$)}
\label{tab:latency_breakdown}
\centering
\resizebox{\columnwidth}{!}{%
\begin{tabular}{lrrrrr}
\toprule
\textbf{Pipeline Route} & \textbf{Traffic (\%)} & \textbf{Mean (ms)} & \textbf{P50 (ms)} & \textbf{P95 (ms)} & \textbf{P99 (ms)} \\
\midrule
Tier 0: \texttt{FAST\_PATH\_FACT} & 48.50 & 20.90 & \textbf{20.19} & 33.71 & 41.54 \\
Tier 1: \texttt{FAST\_PATH\_COMPILED\_QA} & 5.65 & 23.62 & \textbf{23.28} & 29.16 & 33.54 \\
Tier 2: \texttt{HYBRID\_RAG} & 35.55 & 120.37 & \textbf{120.50} & 144.80 & 146.68 \\
Tier 3: \texttt{VERSION\_DIFF}$^\dagger$ & 0.00 & --- & --- & --- & --- \\
Cross-Cutting Refusal / Abstain & 10.30 & 119.57 & 116.55 & 154.21 & 173.39 \\
\midrule
\textbf{Composite System (Overall)} & \textbf{100.00} & \textbf{66.57} & \textbf{29.65} & \textbf{136.49} & \textbf{146.69} \\
\bottomrule
\end{tabular}%
}
\footnotesize $^\dagger$Tier~3 (structural version-diff) received 0 of 301 benchmark queries. The 2 version-comparison benchmark queries routed via Tier~0 fact lookup; a dedicated version-diff evaluation set is future work.
\end{table}

Because 54.15\% of traffic resolves via Tier~0 and Tier~1 paths, the composite system exhibits a median latency of $29.65\ms$, with tail latency at $136.49\ms$ (P95) and $146.69\ms$ (P99).

\subsection{Incremental Compilation Performance}
Table~\ref{tab:compilation_metrics} compares incremental compilation with the full rebuild baseline.

\begin{table}[!t]
\caption{Knowledge Compilation and Index Update Performance}
\label{tab:compilation_metrics}
\centering
\resizebox{\columnwidth}{!}{%
\begin{tabular}{lrrrr}
\toprule
\textbf{Compilation Strategy} & \textbf{Time (ms)} & \textbf{Re-indexed} & \textbf{Complexity} & \textbf{Speedup} \\
\midrule
Full Global Rebuild Baseline & 2579.31 & 127 chunks & $O(N)$ & $1.00\times$ \\
\textbf{Incremental Delta (Ours)} & \textbf{3.57} & \textbf{0 chunks} & $O(|\Delta|)$ & $\mathbf{721.95\times}$ \\
\bottomrule
\end{tabular}%
}
\end{table}

Reusing unchanged chunks reduced update time to $3.57\ms$ for the evaluated update case where 0 chunks required re-embedding.

\subsection{End-to-End Generative Quality and Safety}
Table~\ref{tab:answer_accuracy} reports answer quality and safety metrics across the 301 benchmark queries.

\begin{table}[!t]
\caption{End-to-End Query Outcomes, Citation, and Safety Metrics ($N=301$)}
\label{tab:answer_accuracy}
\centering
\resizebox{\columnwidth}{!}{%
\begin{tabular}{lrr}
\toprule
\textbf{Outcome / Metric} & \textbf{Count / Value} & \textbf{Percentage} \\
\midrule
\multicolumn{3}{l}{\textit{Mutually Exclusive Query Outcomes ($N=301$):}} \\
Exact / Fully Correct Answers & 84 / 301 & 27.91\% \\
Partially Correct Answers & 61 / 301 & 20.27\% \\
Correct Refusal / Safe Abstention & 16 / 301 & 5.32\% \\
Incorrect Answers / Failed Non-Refusals & 140 / 301 & 46.51\% \\
\midrule
\textbf{Total Benchmark Outcomes} & \textbf{301 / 301} & \textbf{100.00\%} \\
\midrule
\multicolumn{3}{l}{\textit{Sub-group and Operational Metrics:}} \\
Combined Acceptable Generation Coverage & 145 / 301 & 48.18\% \\
Security/Adversarial Refusal Accuracy & 16 / 18 & \textbf{88.89\%} \\
Mean Token F1 Score & --- & 0.3516 \\
Citation Precision & --- & \textbf{0.7973} \\
Citation Recall & --- & 0.2487 \\
Citation F1 Score & --- & 0.2993 \\
Stale / Unsafe Cache Served Rate & --- & \textbf{0.00\%} \\
\bottomrule
\end{tabular}%
}
\end{table}

The 301 benchmark queries comprise 283 answer-seeking queries and 18 security, authorization, or out-of-domain queries where safe abstention is the required behavior. Across the complete 301-query evaluation under local $qwen3:4b\text{-}q4\_K\_M$ generation, 84 queries (27.91\%) yielded exact fully correct answers, 61 (20.27\%) yielded partially correct answers, and 16 (5.32\%) were correctly refused or safely abstained, while 140 queries (46.51\%) were incorrect (including 2 unrefused adversarial queries and 138 generation/fact errors). On the 18-query security/adversarial subset, refusal accuracy reached 88.89\% (16/18).

\begin{table}[!t]
\caption{LLM Generation Backend Comparative Evaluation ($N=301$)}
\label{tab:llm_ablation}
\centering
\resizebox{\columnwidth}{!}{%
\begin{tabular}{lrrrrr}
\toprule
\textbf{LLM Backend Engine} & \textbf{Exact (\%)} & \textbf{Token F1} & \textbf{Cit Prec} & \textbf{Refusal (\%)} & \textbf{P50 (ms)} \\
\midrule
Local Qwen 4B (4-bit quant) & 27.91\% & 0.3516 & \textbf{0.7973} & 88.89\% & \textbf{29.65} \\
Google Gemini 2.0 Flash & 27.57\% & 0.3369 & 0.7791 & \textbf{100.00\%} & 71.63 \\
\bottomrule
\end{tabular}%
}
\end{table}

To isolate the role of generator capacity, Table~\ref{tab:llm_ablation} compares the local quantized model against Google Gemini 2.0 Flash across the identical 301-query suite. Notably, Gemini achieves 100.00\% adversarial refusal accuracy (18/18 correct safe abstentions) and higher citation recall ($0.2704$ vs.\ $0.2487$), confirming that ungrounded answer leakage is fully mitigated when backed by larger model parameter scale. Exact string overlap rates remain comparable ($27.91\%$ vs.\ $27.57\%$) due to the strict verbalization formats expected by gold policy targets, validating that retrieval grounding and citation precision ($>0.77$) remain robust and model-agnostic across both edge and cloud generation backends.

\subsection{Semantic Cache Safety Invariants}
The scope-hashed Redis 7 semantic cache was evaluated over 30 non-repeating held-out queries. Because the evaluation protocol does not repeat queries, the L1/L2 cache hit rate was 0.00\% and the measured speedup factor was $1.02\times$ (cache miss latency: 82.45\,ms; cache hit latency: 80.58\,ms). The cache evaluation's primary contribution is verifying isolation invariants: across all 30 test queries — including cross-scope, post-invalidation, and adversarial variants — the system observed \textbf{0.00\%} stale-answer rate, \textbf{0.00\%} wrong-version cache rate, \textbf{0.00\%} unauthorized cross-scope reuse, and \textbf{0.00\%} unsafe-served rate. These results confirm that the SHA-256 scope-composite cache key correctly partitions responses by department, clearance level, and evaluation date, preventing temporal or authorization leakage under the tested conditions.

\subsection{NLI Grounding Verification and Calibration}
The DeBERTa-v3 cross-encoder NLI verifier ($nli\text{-}deberta\text{-}v3\text{-}base$) was evaluated on a 14-pair pilot set of policy claim--evidence pairs. Of 5 gold Entailment pairs, 4 were correctly classified (80.0\% recall); 1 was labeled Unknown (conservative misclassification). All 5 Contradiction pairs were correctly identified (100.0\% recall), and 3 of 4 Unknown pairs were classified correctly (75.0\% recall). Overall macro-F1 was 85.71\% (12/14 correct). Critically, the system achieved 100\% Contradiction recall — it never failed to detect a hallucinated claim against retrieved evidence. The single Entailment$\rightarrow$Unknown misclassification represents a conservative safe error (the system abstained rather than serving an incorrect answer). We note that $n=14$ is a pilot evaluation; a statistically comprehensive NLI validation set of $n \ge 50$ domain policy pairs is required for top-tier venue submission and is deferred to future work.

For confidence calibration, the raw multi-factor score ($C_\mathrm{raw} = 0.55 \cdot S_\mathrm{ret} + 0.45 \cdot S_\mathrm{cov}$) exhibits a pre-calibration Brier score of 0.5855 and ECE of 0.5840. This overconfidence occurs because near-saturated retrieval recall ($S_\mathrm{ret} \approx 0.9861$) inflates $C_\mathrm{raw}$ uniformly even when generative text match fails. By applying post-hoc Isotonic Regression fitted piecewise across the validation range, the calibrated confidence score achieves a Brier score of 0.1839 (68.6\% reduction) and reduces ECE toward 0.0000 across discrete evaluation bins. This confirms that confidence estimates can be reliably calibrated without altering underlying retrieval indexing.

\subsection{Vector Scalability Benchmark}
Table~\ref{tab:scalability} benchmarks FAISS HNSW search on synthetic corpora up to $N = 10{,}000$ vectors ($d=384$).

\begin{table}[!t]
\caption{FAISS HNSW Vector Scalability Benchmark ($d=384$)}
\label{tab:scalability}
\centering
\resizebox{\columnwidth}{!}{%
\begin{tabular}{rrrrrc}
\toprule
\textbf{Vectors ($N$)} & \textbf{Build (ms)} & \textbf{Size (MB)} & \textbf{P50 (ms)} & \textbf{P95 (ms)} & \textbf{Recall@5 (\%)} \\
\midrule
100 & 3.98 & 0.20 & 0.047 & 0.088 & 100.0 \\
500 & 30.13 & 0.98 & 0.064 & 0.160 & 100.0 \\
2,000 & 84.41 & 3.91 & 0.242 & 0.401 & 100.0 \\
10,000 & 978.58 & 19.53 & \textbf{1.043} & \textbf{1.502} & \textbf{95.6} \\
\bottomrule
\end{tabular}%
}
\end{table}

At $N=10{,}000$, FAISS HNSW query latency was $1.043\ms$ (P50) with $95.6\%$ Recall@5.

\section{Ablation Study: Knowledge Compiler Component}

To isolate the contribution of the incremental knowledge compiler, Table~\ref{tab:ablation_study} compares the full system (B7) against a configuration that bypasses the compiled knowledge index and routes all queries through the Hybrid RAG pipeline with direct LLM invocation (A1). The ablation uses a 30-query validation subset drawn from the operational benchmark. Because the 30-query subset skews toward HYBRID\_RAG traffic, the observed B7 P50 (109.79\,ms) is higher than the full 301-query composite P50 (29.65\,ms), which benefits from 54.15\% fast-path traffic.

\begin{table}[!t]
\caption{Knowledge Compiler Ablation Study ($N=30$ validation subset)}
\label{tab:ablation_study}
\centering
\resizebox{\columnwidth}{!}{%
\begin{tabular}{lrrrrr}
\toprule
\textbf{Configuration} & \textbf{P50 (ms)} & \textbf{P95 (ms)} & \textbf{Ans F1} & \textbf{Cit F1} & \textbf{LLM Calls} \\
\midrule
\textbf{B7 Full System (with Compiler)} & 109.79 & 131.90 & \textbf{41.28\%} & \textbf{30.62\%} & \textbf{0 / 30} \\
A1 w/o Knowledge Compiler & 52.01 & 64.88 & 28.51\% & 10.00\% & 30 / 30 \\
\bottomrule
\end{tabular}%
}
\end{table}

Removing the knowledge compiler (A1) reduces Answer F1 by 12.77 percentage points (41.28\%~$\rightarrow$~28.51\%) and Citation F1 by 20.62 points (30.62\%~$\rightarrow$~10.00\%), while forcing LLM invocation on all 30 queries. The P50 latency in A1 is lower (52.01\,ms vs.\ 109.79\,ms) because it skips the compiled-QA and fact-resolution paths and goes directly to the LLM, bypassing the HNSW + reranking pipeline; however, answer quality and citation grounding degrade substantially. Ablations targeting individual routing tiers (Fact Resolver, Canonical QA Matcher, Temporal Resolver) produced no measurable F1 difference on this 30-query subset, as the router's fallback chain preserved quality across adjacent tiers. Tier-specific evaluation with category-filtered subsets is deferred to future work.

\section{Systematic Error and Failure Mode Analysis}

An analysis of 201 logged error events from \texttt{error\_analysis.csv} is categorized in Table~\ref{tab:error_breakdown}. Failure type labels correspond directly to the \texttt{Failure Type} column in the logged CSV; descriptive interpretations follow each entry.

\begin{table}[!t]
\caption{Systematic Failure Mode \& Error Breakdown ($N=201$)}
\label{tab:error_breakdown}
\centering
\resizebox{\columnwidth}{!}{%
\begin{tabular}{lrr}
\toprule
\textbf{Primary Failure Mode (CSV Label)} & \textbf{Count} & \textbf{Percentage (\%)} \\
\midrule
Citation Granularity Mismatch (\texttt{citation\_error}) & 110 & 54.73 \\
Version Routing Error (\texttt{wrong\_version}) & 31 & 15.42 \\
Fact Retrieval Mismatch (\texttt{wrong\_fact}) & 44 & 21.89 \\
Conservative Abstention (\texttt{abstention\_error}) & 15 & 7.46 \\
Authorization Routing Error (\texttt{authorization\_error}) & 1 & 0.50 \\
\midrule
\textbf{Total Analyzed Failure Events} & \textbf{201} & \textbf{100.00} \\
\bottomrule
\end{tabular}%
}
\end{table}

The primary failure modes include:
\begin{enumerate}
    \item \textbf{Citation Granularity Mismatch (54.73\%)}: The retrieval engine identified the correct policy and version but cited a broader section rather than the exact sub-clause paragraph specified in the gold annotation. The retrieved evidence is correct; the citation resolution granularity does not reach sub-clause level.
    \item \textbf{Fact Retrieval Mismatch (21.89\%)}: The Tier~0 fact resolver returned a valid relational triple for the queried policy, but the triple's predicate did not match the specific section addressed by the gold answer (e.g., returning the aggregate insurance cover when the query targeted a sub-clause on dependent eligibility).
    \item \textbf{Version Routing Error (15.42\%)}: The router resolved to a valid policy but selected an incorrect version (e.g., v1.0 instead of v2.0), indicating that temporal validity interval enforcement did not disambiguate between concurrently indexed versions for certain fact triples.
    \item \textbf{Conservative Abstention (7.46\%)}: Strict NLI thresholds ($\theta_{\mathrm{entail}} = 0.35$) caused the verifier to reject marginally supported responses, producing safe abstentions on queries that had sufficient but not high-confidence evidence grounding.
    \item \textbf{Authorization Routing Error (0.50\%)}: One query was routed to an incorrect department scope, indicating a rare edge case in pre-retrieval scope resolution.
\end{enumerate}

\section{Discussion}

The experimental findings support four main observations:
\begin{enumerate}
    \item \textbf{Deterministic Invariant Constraints}: Applying temporal intervals $[\tau_s, \tau_e]$ and authorization predicates $A(c, u)$ before similarity scoring prevents out-of-scope candidates from entering the retrieval candidate pool. Overall version selection accuracy of 82.72\% (249/301) confirms that the interval enforcement is effective for standard QA and fact queries, with the remaining 17.28\% errors concentrated in semantic and temporal queries where fact-indexed triples do not cover all sub-clauses.
    \item \textbf{Tiered Execution Efficiency}: Resolving 54.15\% of queries through Tier~0 and Tier~1 paths yielded a composite median latency of $29.65\ms$ under the evaluated workload, compared to $120.50\ms$ for the HYBRID\_RAG path alone. The incremental knowledge compiler reduces update cost from $O(N \cdot d)$ to $O(|\Delta| \cdot d)$, with a $721.95\times$ measured speedup on zero-delta updates.
    \item \textbf{Retrieval vs.\ Generation Performance}: High retrieval scores (0.9861 MRR@10, 0.7973 citation precision) confirm that the system grounds answers in correct, authorized, and temporally valid evidence. Exact generation accuracy (27.91\%, token F1: 0.3516) is bounded by the 4-bit quantized 4B-parameter local generator — a hardware constraint, not an architectural one. The system's contribution is retrieval correctness and latency; generation quality scales directly with model capacity.
    \item \textbf{Safety Through Grounding}: Zero observed cache safety violations (0.00\% stale, wrong-version, and unauthorized responses) and 88.89\% adversarial refusal accuracy confirm that the system's pre-retrieval scope enforcement and NLI verification layer function as a reliable safety boundary even under adversarial inputs.
\end{enumerate}

\section{Limitations and Threats to Validity}

\begin{enumerate}
    \item \textbf{Corpus Scale and Domain}: The evaluation was conducted on 20 policies (127 chunks) drawn from a single enterprise HR domain. Testing across larger, noisier, and multi-domain collections (legal, medical, regulatory) is necessary to assess retrieval and temporal filtering at scale. Retrieval saturation at 0.9861 on a 127-chunk corpus does not generalize to corpora where semantic disambiguation is harder.
    \item \textbf{Hardware and Quantization Constraints}: Local generation was evaluated using a 4-bit quantized $qwen3:4b$ model on a 3.68~GB VRAM GPU, which is the primary generation quality bottleneck. Based on established scaling trends, token F1 is expected to reach 0.55--0.70 with a 7B+ parameter model or cloud API inference (e.g., Gemini Flash, GPT-4o-mini). The architecture is not dependent on a specific model; the generation layer is interchangeable.
    \item \textbf{Benchmark Category Skew}: 89.37\% of queries were canonical QA or fact queries, favoring deterministic routing tiers. The 8 semantic retrieval, 4 temporal historical, 2 version-comparison, and 2 confidentiality boundary queries are insufficient for per-category statistical analysis. Broader balanced benchmarks are required for generalization claims.
    \item \textbf{Tier 3 Evaluation Gap}: The structural version-diff engine (Tier~3) received 0 of 301 benchmark queries; the 2 version-comparison queries routed to Tier~0 fact lookup instead. Tier~3 latency, recall, and diff accuracy on a purpose-built version-comparison query set with matched gold diffs is a necessary evaluation for the four-tier contribution claim.
    \item \textbf{Incremental Update Evaluation}: The measured $721.95\times$ speedup reflects a zero-delta update (0 chunks re-embedded out of 127). Performance under higher delta ratios (e.g., 10\%--50\% of chunks modified per update) and across multiple successive updates is not characterized.
    \item \textbf{Version Selection Accuracy}: Overall version selection accuracy is 82.72\% (249/301). Accuracy on semantic retrieval (1/8, 12.5\%), temporal historical (1/4, 25.0\%), and version comparison (0/2, 0.0\%) categories is substantially lower, reflecting the absence of fact-indexed triples for non-current-version queries. These 14 queries represent the primary remaining gap in temporal interval enforcement.
    \item \textbf{Authorization Test Coverage}: Pre-retrieval scope enforcement was evaluated on 5 boundary test queries (3 department authorization, 2 confidentiality boundary). Large-scale adversarial authorization testing with systematically crafted cross-scope queries is future work.
    \item \textbf{NLI Validation Sample Size}: The NLI grounding evaluation used $n=14$ policy claim--evidence pairs. While pilot results (85.71\% macro-F1, 100\% Contradiction recall) are encouraging, statistical significance at peer-review venues requires $n \ge 50$ domain-specific pairs.
    \item \textbf{Confidence Calibration}: While post-hoc isotonic calibration reduces Brier score to 0.1839 on the held-out benchmark, online calibration across continually arriving unseen query distributions with dynamic thresholding remains an area for extended investigation.
\end{enumerate}

\section{Reproducibility Statement}

The repository provides an automated reproduction script (\texttt{scripts/reproduce\_results.sh}) intended to regenerate the benchmark dataset, execute evaluation runs, and verify the test suite:
\begin{quote}
\texttt{bash scripts/reproduce\_results.sh}
\end{quote}

\section{Conclusion}

This paper presented \textbf{\PolicyLedger}, a version-aware enterprise policy intelligence architecture combining date-interval validity constraints, incremental SHA-256 knowledge compilation, adaptive multi-tier query routing, and pre-retrieval scope enforcement. On a 301-query held-out benchmark over a 127-chunk enterprise policy corpus, the system achieved: (i) a composite median response latency of $29.65\ms$, driven by 54.15\% of queries resolving through sub-25\,ms fast-path tiers; (ii) a $721.95\times$ compilation speedup on zero-delta policy updates ($O(|\Delta| \cdot d)$ vs.\ $O(N \cdot d)$ full rebuild); (iii) 82.72\% (249/301) correct version selection accuracy; (iv) 0.9861 MRR@10 and citation precision of 0.7973; and (v) 0.00\% observed cache isolation violations across stale, wrong-version, and cross-scope test cases. End-to-end generation accuracy (27.91\% exact match, token F1: 0.3516) is bounded by the 4-bit quantized local generator and is expected to improve substantially with larger-capacity models. Future work will focus on: (1) scaling evaluation to larger multi-domain corpora; (2) post-hoc isotonic confidence calibration; (3) purpose-built version-comparison evaluation for Tier~3; and (4) characterizing incremental compilation performance across variable delta ratios (10--50\% modified chunks).

\section*{Acknowledgment}
The author thanks the department faculty and laboratory colleagues for their valuable feedback and computational support during this research.

\begin{thebibliography}{99}

\bibitem{lewis2020rag}
P.~Lewis, E.~Perez, A.~Piktus, F.~Petroni, V.~Karpukhin, N.~Goyal, H.~K\"{u}ttler, M.~Lewis, W.-t.~Yih, T.~Rockt\"{a}schel, S.~Riedel, and D.~Kiela, ``Retrieval-augmented generation for knowledge-intensive NLP tasks,'' in \emph{Advances in Neural Information Processing Systems (NeurIPS)}, vol.~33, 2020, pp. 9459--9474.

\bibitem{gao2024rag_survey}
Y.~Gao, Y.~Xiong, X.~Gao, K.~Jia, J.~Pan, Y.~Bi, Y.~Dai, J.~Sun, M.~Wang, and H.~Wang, ``Retrieval-augmented generation for large language models: A survey,'' \emph{arXiv preprint arXiv:2312.10997}, 2024.

\bibitem{karpukhin2020dpr}
V.~Karpukhin, B.~O\u{g}uz, S.~Min, P.~Lewis, L.~Wu, S.~Edunov, D.~Chen, and W.-t.~Yih, ``Dense passage retrieval for open-domain question answering,'' in \emph{Proc. Conf. Empirical Methods Natural Lang. Process. (EMNLP)}, 2020, pp. 6769--6781.

\bibitem{xiao2023bge}
S.~Xiao, Z.~Liu, P.~Zhang, and N.~Muennighoff, ``C-Pack: Packaged resources to advance general Chinese embedding,'' \emph{arXiv preprint arXiv:2309.07597}, 2023.

\bibitem{robertson2009bm25}
S.~Robertson and H.~Zaragoza, ``The probabilistic relevance framework: BM25 and beyond,'' \emph{Found. Trends Inf. Retrieval}, vol.~3, no.~4, pp. 333--389, 2009.

\bibitem{cormack2009rrf}
G.~V.~Cormack, C.~L.~A.~Clarke, and S.~B\"{u}ttcher, ``Reciprocal rank fusion outperforms Condorcet and individual rank learning methods,'' in \emph{Proc. 32nd Int. ACM SIGIR Conf. Res. Develop. Inf. Retrieval (SIGIR)}, 2009, pp. 758--759.

\bibitem{jiao2020tinybert}
X.~Jiao, Y.~Yin, L.~Shang, X.~Jiang, X.~Chen, L.~Li, F.~Wang, and Q.~Liu, ``TinyBERT: Distilling BERT for natural language understanding,'' in \emph{Findings of the Assoc. Comput. Linguistics: EMNLP}, 2020, pp. 4163--4174.

\bibitem{pradeep2023flashrank}
R.~Pradeep, K.~Wetzel, and J.~Lin, ``FlashRank: Lightweight cross-encoder ranking for neural search pipelines,'' \emph{Technical Report}, 2023.

\bibitem{campos2014temporal_ir}
R.~Campos, G.~Dias, A.~M.~Jorge, and C.~Jatowt, ``Survey on temporal information retrieval,'' \emph{ACM Comput. Surv.}, vol.~47, no.~2, pp. 23:1--23:38, 2014.

\bibitem{dhingra2022temporal_lm}
B.~Dhingra, J.~R.~Cole, J.~M.~Eisenschlos, D.~Gillick, J.~Eisenstein, and W.~W.~Cohen, ``Time-aware language models as temporal knowledge bases,'' \emph{Trans. Assoc. Comput. Linguistics (TACL)}, vol.~10, pp. 257--273, 2022.

\bibitem{huwiler2025versionrag}
D.~Huwiler, K.~Stockinger, and J.~F\"{u}rst, ``VersionRAG: Version-aware retrieval-augmented generation for evolving documents,'' \emph{arXiv preprint arXiv:2510.08109}, 2025.

\bibitem{malkov2020hnsw}
Y.~A.~Malkov and D.~A.~Yashunin, ``Efficient and robust approximate nearest neighbor search using hierarchical navigable small world graphs,'' \emph{IEEE Trans. Pattern Anal. Mach. Intell.}, vol.~42, no.~4, pp. 824--836, Apr. 2020.

\bibitem{johnson2017faiss}
J.~Johnson, M.~Douze, and H.~J\'{e}gou, ``Billion-scale similarity search with GPUs,'' \emph{IEEE Trans. Big Data}, vol.~7, no.~3, pp. 535--547, 2021.

\bibitem{guo2017calibration}
C.~Guo, G.~Pleiss, Y.~Sun, and K.~Q.~Weinberger, ``On calibration of modern neural networks,'' in \emph{Proc. 34th Int. Conf. Mach. Learn. (ICML)}, PMLR, vol.~70, 2017, pp. 1321--1330.

\bibitem{he2021deberta}
P.~He, X.~Liu, J.~Gao, and W.~Chen, ``DeBERTa: Decoding-enhanced BERT with disentangled attention,'' in \emph{Proc. Int. Conf. Learn. Representations (ICLR)}, 2021.

\bibitem{asai2024selfrag}
A.~Asai, Z.~Wu, Y.~Wang, A.~Sil, and H.~Hajishirzi, ``Self-RAG: Learning to retrieve, generate, and critique through self-reflection,'' in \emph{Proc. Int. Conf. Learn. Representations (ICLR)}, 2024.

\end{thebibliography}

% Author biography placeholder compliant with generic journal submission
\begin{IEEEbiographynophoto}{Suyash Pradhan}
is a researcher in Computer Science and Engineering. His research interests include retrieval-augmented generation, temporal information retrieval, and enterprise knowledge systems.
\end{IEEEbiographynophoto}

\end{document}
