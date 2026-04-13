"use client";
import { useState} from "react";

export default function Home() {

  const [input, setInput] = useState("");
  const [response, setResponse] = useState("");



  const handleAsk = async () =>{
    console.log(input)
    const res = await fetch("http://localhost:8000/stream");

    const reader = res.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) return;

    let result = "";
    while (true) {
      const {done, value} = await reader.read();
      if(done) break;
      result += decoder.decode(value);
      setResponse(result);
    }
  };


  return (
    <div className="flex flex-col flex-1 items-center justify-center bg-zinc-50 font-sans dark:bg-black">
      <main className="flex flex-1 w-full max-w-3xl flex-col items-center justify-between py-32 px-16 bg-white dark:bg-black sm:items-start">
        <div>
          <input className="border-4 border-white-500" value = {input} onChange={(e)=> setInput(e.target.value)} />
          <button onClick={handleAsk}>Ask</button>
          <p>{response}</p>
        </div>
      </main>
    </div>
  );
}
