(()=>{"use strict";
  const nativeFetch=window.fetch.bind(window);
  const canonical="./data/current.json";
  let firstUsed=false;
  const first=nativeFetch(canonical,{cache:"no-cache"});

  const isCurrent=input=>{
    const url=typeof input==="string"?input:String(input?.url||input||"");
    return /(?:^|\/)data\/current\.json(?:[?#]|$)/.test(url);
  };

  window.fetch=(input,init)=>{
    if(!isCurrent(input))return nativeFetch(input,init);
    if(!firstUsed){
      firstUsed=true;
      return first.then(response=>response.clone()).catch(()=>nativeFetch(canonical,{...(init||{}),cache:"no-cache"}));
    }
    return nativeFetch(canonical,{...(init||{}),cache:"no-cache"});
  };
})();