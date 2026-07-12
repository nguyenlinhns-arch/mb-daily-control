(()=>{"use strict";
  const app=document.getElementById("app");
  if(!app)return;
  let applying=false;
  function enforce(){
    if(applying)return;
    applying=true;
    try{
      app.querySelectorAll("details").forEach(node=>node.remove());
      [...app.querySelectorAll("section.section")].forEach(section=>{
        const heading=String(section.querySelector("h2")?.textContent||"").toUpperCase();
        if(heading.includes("CHI TIẾT")||heading.includes("MỐC VÀO")){
          section.remove();
          return;
        }
        if(heading.includes("THEO DÕI VỐN")||heading.includes("LỢI NHUẬN")){
          const h2=section.querySelector("h2");
          const desc=section.querySelector(".section-head p");
          if(h2)h2.textContent="Lũy kế đã khóa & vốn kỳ sắp tới";
          if(desc)desc.textContent="Kết quả kỳ đã khóa đã được cộng vào lũy kế; không hiển thị lại dữ kiện kỳ cũ.";
          section.querySelectorAll(".pnl-card").forEach(card=>{
            const label=String(card.querySelector("span")?.textContent||"");
            const keep=label.includes("Tổng toàn bộ")||label.includes("Lệnh hôm nay chờ KQ")||label.includes("Vốn kỳ sắp tới");
            if(!keep){card.remove();return;}
            const span=card.querySelector("span");
            const small=card.querySelector("small");
            if(label.includes("Tổng toàn bộ")&&span){
              span.textContent="Lũy kế đã khóa";
              if(small)small.textContent="Đã cộng kết quả đến kỳ dữ liệu gần nhất";
            }
            if((label.includes("Lệnh hôm nay chờ KQ")||label.includes("Vốn kỳ sắp tới"))&&span){
              span.textContent="Vốn kỳ sắp tới";
              if(small)small.textContent=String(small.textContent||"").replace(" · chưa cộng P/L","");
            }
          });
        }
      });
    }finally{applying=false;}
  }
  new MutationObserver(enforce).observe(app,{childList:true,subtree:true});
  enforce();
})();
