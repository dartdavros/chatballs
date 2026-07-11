A deliberately plain document editor (title + textarea, no rich-text toolbar) for AI knowledge-base entries and prompts — matches Hub's "no reinventing standard patterns" rule by staying as unadorned as possible.

```jsx
<KnowledgeDocumentEditor title={t} onTitleChange={e=>setT(e.target.value)} docId="KB-0091" body={b} onBodyChange={e=>setB(e.target.value)} />
```
