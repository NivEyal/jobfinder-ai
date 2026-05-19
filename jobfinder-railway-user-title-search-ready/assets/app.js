/* JobFinder — app.js */

// Navbar scroll
(function(){
  var nav=document.querySelector('.lp-nav')||document.querySelector('.site-nav');
  if(!nav)return;
  window.addEventListener('scroll',function(){nav.classList.toggle('lp-nav-scrolled',window.scrollY>20);nav.classList.toggle('scrolled',window.scrollY>20);},{passive:true});
})();

// Mobile hamburger
(function(){
  var btn=document.getElementById('lp-burger')||document.getElementById('nav-hamburger');
  var menu=document.getElementById('lp-mobile-menu')||document.getElementById('nav-mobile-menu');
  if(!btn||!menu)return;
  btn.addEventListener('click',function(){btn.classList.toggle('open');menu.classList.toggle('open');});
})();

// Scroll reveal
(function(){
  var els=document.querySelectorAll('.lp-reveal,.reveal');
  if(!els.length)return;
  var io=new IntersectionObserver(function(entries){
    entries.forEach(function(e,i){if(e.isIntersecting){setTimeout(function(){e.target.classList.add('lp-visible');e.target.classList.add('visible');},i*70);io.unobserve(e.target);}});
  },{threshold:0.08});
  els.forEach(function(el){io.observe(el);});
})();

// ── Progress / Loading ──
var progressTimer=null;

function setProgress(data){
  var count=document.getElementById('loading-count');
  var bar=document.getElementById('loading-progress-bar');
  var msg=document.getElementById('loading-message');
  var found=data.jobs_found_so_far||0;
  var target=data.target_jobs||100;
  var pct=data.percent||Math.min(100,Math.round(found/Math.max(target,1)*100));
  if(count)count.textContent='נמצאו '+found+' מתוך '+target+' משרות';
  if(bar)bar.style.width=pct+'%';
  if(msg&&data.message)msg.textContent=data.message;
}

async function pollProgress(){
  try{var r=await fetch('/api/progress',{cache:'no-store'});if(r.ok)setProgress(await r.json());}catch(e){}
}

async function cancelSearch(){
  var btn=document.getElementById('cancel-search-button');
  if(btn){btn.disabled=true;btn.textContent='עוצר...';}
  try{var r=await fetch('/api/cancel-search',{method:'POST'});if(r.ok)setProgress(await r.json());}catch(e){}
}

function showLoading(form){
  var overlay=document.getElementById('loading-overlay');
  if(overlay)overlay.hidden=false;
  setProgress({jobs_found_so_far:0,target_jobs:100,percent:1,message:'מתחיל חיפוש...'});
  if(progressTimer)clearInterval(progressTimer);
  progressTimer=setInterval(pollProgress,1000);
  form.querySelectorAll('button').forEach(function(b){b.disabled=true;b.dataset.orig=b.textContent;b.textContent='טוען...';});
}

document.querySelectorAll('form').forEach(function(form){
  form.addEventListener('submit',async function(event){
    var action=form.getAttribute('action')||'';
    var isAsync=action==='/api/run-ui'||action==='/api/apply-all';
    showLoading(form);
    if(!isAsync)return;
    event.preventDefault();
    try{
      var r=await fetch(action,{method:'POST',body:new FormData(form),redirect:'manual'});
      var data={};
      try{data=await r.json();}catch(e){}
      var redirect=data.redirect||'/dashboard';
      // Poll until pipeline completes
      var done=setInterval(async function(){
        await pollProgress();
        try{
          var pr=await fetch('/api/progress',{cache:'no-store'});
          var pd=await pr.json();
          if(['complete','cancelled','failed'].includes(pd.phase)){
            clearInterval(done);
            if(progressTimer)clearInterval(progressTimer);
            window.location.href=redirect;
          }
        }catch(e){}
      },1200);
    }catch(err){
      var m=document.getElementById('loading-message');
      if(m)m.textContent='אירעה שגיאה. נסה שוב בעוד רגע.';
      if(progressTimer)clearInterval(progressTimer);
    }
  });
});

var cancelBtn=document.getElementById('cancel-search-button');
if(cancelBtn)cancelBtn.addEventListener('click',cancelSearch);
