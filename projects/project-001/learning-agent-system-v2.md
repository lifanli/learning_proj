# Learning Agent System - Updated Proposal v2.0

**Version**: v2.0  
**Updated**: 2026-03-06 13:23 UTC  
**Status**: Awaiting Review  

---

## Executive Summary

Building a **multi-agent collaborative learning system** where AI agents provide personalized learning experiences.

**Key Features**:
- Multi-agent collaboration (Teacher, Assistant, Evaluator, Searcher)
- Personalized learning paths
- Continuous improvement from feedback
- Open technology stack (MinIO/LightRAG are recommendations, not mandates)

---

## Team Roles

| Role | Responsibility | Status |
|------|----------------|--------|
| **Frontend Engineer** | UI development, interaction | ✅ Active |
| **Review Worker** | Review outputs, ask questions | ✅ Active |
| **Search Worker** | Search new tech, share knowledge | ✅ Active |
| **Backend Engineer** | Backend services, API | ⏳ To create |
| **Architect** | System architecture, decisions | ⏳ To create |

---

## Technology Stack (Open for Discussion)

### Frontend

| Layer | Recommended | Alternatives | Status |
|-------|-------------|--------------|--------|
| **Framework** | React 18 + TypeScript | Vue 3 + TypeScript | Open |
| **State** | Zustand + React Query | Pinia / Redux | Open |
| **UI** | shadcn/ui + Tailwind | Ant Design / Element | Open |
| **Build** | Vite | Webpack / Turbopack | Open |
| **Real-time** | WebSocket + SSE | GraphQL Subscriptions | Open |

### Backend (To Discuss)

| Layer | Recommended | Alternatives | Status |
|-------|-------------|--------------|--------|
| **Runtime** | Node.js / Python | Go / Rust | Open |
| **Framework** | FastAPI / Express | NestJS / Gin | Open |
| **Database** | PostgreSQL + pgvector | MongoDB / MySQL | Open |
| **Vector DB** | LightRAG (recommended) | Chroma / Milvus | Open |
| **Storage** | MinIO (recommended) | S3 / Local | Open |

---

## Search Worker Tasks

@search-worker Please search and document:

| Topic | Priority | Purpose |
|-------|----------|---------|
| **MinIO** | High | Object storage for files/resources |
| **LightRAG** | High | RAG implementation for knowledge retrieval |
| **pgvector** | Medium | Vector database for semantic search |
| **Multi-agent Architecture** | Medium | Agent collaboration patterns |

**Output Location**: `shared/knowledge/search-results/2026-03/`  
**Deadline**: 30 min per topic

---

## Review Worker Tasks

@review-worker Please review the frontend proposal:

1. **Tech Stack**: Is React + TypeScript the right choice?
2. **Architecture**: Is the multi-agent UI design sufficient?
3. **Risks**: What are the potential technical risks?
4. **Edge Cases**: What scenarios are missing?
5. **Feasibility**: Is 5 weeks realistic?
6. **Dependencies**: Is collaboration with backend/search clear?

**Expected Questions**: 3-7  
**Deadline**: 2 hours  

---

## Next Steps

| Action | Owner | Status |
|--------|-------|--------|
| Activate Search Worker | Manager | Pending |
| Execute MinIO/LightRAG search | Search Worker | Pending |
| Review frontend proposal | Review Worker | Pending |
| Clarify requirements | Human Admin | Pending |
| Tech stack decisions | Team | Pending |

---

**Status**: Updated v2.0  
**Last Updated**: 2026-03-06 13:23 UTC  
**Next**: Awaiting Search Worker and Review Worker input
