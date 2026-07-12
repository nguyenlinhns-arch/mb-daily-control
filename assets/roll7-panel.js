(()=>{"use strict";
  const app=document.getElementById("app");
  if(!app)return;

  function patch(){
    const cards=[...app.querySelectorAll("article.method-card")];
    const card=cards.find(node=>String(node.querySelector("h3")?.textContent||"").toUpperCase().includes("ROLL7"));
    if(!card)return;
    card.classList.remove("method-generic");
    card.classList.add("method-roll7");
    const symbol=card.querySelector(".method-symbol");
    const kicker=card.querySelector(".method-kicker");
    if(symbol)symbol.textContent="R7";
    if(kicker)kicker.textContent="Cứu độ phủ";

    const facts=app.querySelector(".hero .facts");
    if(facts&&!facts.querySelector(".roll7-fact")){
      const status=String(card.querySelector(".status-pill")?.textContent||"—");
      const fact=document.createElement("div");
      fact.className="fact roll7-fact";
      fact.innerHTML=`<span>ROLL7</span><b>${status}</b>`;
      facts.appendChild(fact);
    }else if(facts){
      const target=facts.querySelector(".roll7-fact b");
      if(target)target.textContent=String(card.querySelector(".status-pill")?.textContent||"—");
    }
  }

  new MutationObserver(patch).observe(app,{childList:true,subtree:true});
  patch();
})();
