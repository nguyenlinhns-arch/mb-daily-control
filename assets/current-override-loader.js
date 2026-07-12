(()=>{"use strict";
  const nativeFetch=window.fetch.bind(window);
  window.fetch=async(input,init)=>{
    const url=String(input||"");
    if(url.includes("./data/current.json")){
      try{
        const response=await nativeFetch(`./data/current-override.json?v=${Date.now()}`,{...(init||{}),cache:"no-store"});
        if(response.ok){
          const probe=response.clone();
          const doc=await probe.json();
          const expires=Date.parse(String(doc.valid_until||""));
          if(!Number.isFinite(expires)||expires>=Date.now()) return response;
        }
      }catch(_err){/* fall through to canonical payload */}
    }
    return nativeFetch(input,init);
  };
})();
