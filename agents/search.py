import chromadb
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

def get_client():
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# In-memory ChromaDB client
chroma_client = chromadb.Client()

def index_transcript(transcript_data: dict, video_id: str) -> dict:
    """Index transcript chunks into ChromaDB for semantic search"""
    
    if not transcript_data.get("success"):
        return {"success": False, "error": "No valid transcript to index"}
    
    try:
        collection_name = f"video_{video_id}"
        
        try:
            chroma_client.delete_collection(collection_name)
        except:
            pass
        
        collection = chroma_client.create_collection(collection_name)
        
        chunks = transcript_data["chunks"]
        
        segments = []
        segment_size = 5
        
        for i in range(0, len(chunks), segment_size):
            group = chunks[i:i + segment_size]
            text = " ".join([c["text"] for c in group])
            start = group[0]["start"]
            minutes = int(start // 60)
            seconds = int(start % 60)
            timestamp = f"{minutes:02d}:{seconds:02d}"
            
            segments.append({
                "id": str(i),
                "text": text,
                "timestamp": timestamp,
                "start_seconds": start
            })
        
        collection.add(
            documents=[s["text"] for s in segments],
            ids=[s["id"] for s in segments],
            metadatas=[{
                "timestamp": s["timestamp"],
                "start_seconds": s["start_seconds"]
            } for s in segments]
        )
        
        return {
            "success": True,
            "collection_name": collection_name,
            "segments_indexed": len(segments)
        }
        
    except Exception as e:
        return {"success": False, "error": f"Indexing failed: {str(e)}"}


def search_transcript(question: str, video_id: str, language: str = "English") -> dict:
    """Agent 3 - Search: Find the moment in the lecture that answers the question"""
    
    client = get_client()
    try:
        collection_name = f"video_{video_id}"
        collection = chroma_client.get_collection(collection_name)
        
        results = collection.query(
            query_texts=[question],
            n_results=3
        )
        
        if not results["documents"][0]:
            return {"success": False, "error": "No relevant moments found"}
        
        context = ""
        timestamps = []
        for i, doc in enumerate(results["documents"][0]):
            timestamp = results["metadatas"][0][i]["timestamp"]
            timestamps.append(timestamp)
            context += f"[{timestamp}] {doc}\n\n"
        
        language_instruction = f"Answer in {language}." if language and language != "English" else ""

        response = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": f"""A student asked: "{question}"

        Based on these moments from the lecture:
        {context}

        Give a clear, direct answer to the student's question.
        Then tell them exactly which timestamp to jump to for more context.
        Keep your answer under 150 words.
        {language_instruction}"""
            }]
        )
        
        answer = response.choices[0].message.content
        
        return {
            "success": True,
            "answer": answer,
            "timestamps": timestamps,
            "primary_timestamp": timestamps[0] if timestamps else None
        }
        
    except Exception as e:
        return {"success": False, "error": f"Search failed: {str(e)}"}