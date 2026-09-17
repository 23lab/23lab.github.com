// 果蝇全脑 LIF 模拟器。既可作为 Web Worker 脚本加载，也可在主线程内联运行（见 index.html）。
let N,indptr,indices,w;
function parse(buf){
  const dv=new DataView(buf); if(String.fromCharCode(dv.getUint8(0),dv.getUint8(1),dv.getUint8(2),dv.getUint8(3))!=='FLYW') throw new Error('bad file');
  N=dv.getUint32(4,true); const nnz=dv.getUint32(8,true); let o=12;
  indptr=new Uint32Array(buf,o,N+1); o+=(N+1)*4;
  indices=new Uint32Array(buf,o,nnz); o+=nnz*4;
  w=new Int16Array(buf,o,nnz); o+=nnz*2;
  const sc=new Uint8Array(buf,o,N); o+=N; const side=new Uint8Array(buf,o,N); o+=N;
  const ct=new Uint16Array(buf.slice(o,o+N*2)); o+=N*2;
  const hi=new Uint32Array(buf.slice(o,o+N*4)); o+=N*4; const lo=new Uint32Array(buf.slice(o,o+N*4)); o+=N*4;
  const px=new Uint16Array(buf.slice(o,o+N*2)); o+=N*2; const py=new Uint16Array(buf.slice(o,o+N*2));
  const nt=new Int8Array(N); for(let i=0;i<N;i++) nt[i]=indptr[i+1]>indptr[i]?(w[indptr[i]]<0?-1:1):0;
  return {N,nnz,sc:sc.slice(),side:side.slice(),ct,hi,lo,px,py,nt};
}
function run(p){
  const dt=0.1,vRest=-52,vTh=-45,taum=20,taus=5,tRefr=2.2,delay=1.8,wSyn=0.275;
  const dm=Math.exp(-dt/taum),ds=Math.exp(-dt/taus),gain=1-dm;
  const steps=Math.round(p.tRun/dt),delaySteps=Math.round(delay/dt),refrSteps=Math.round(tRefr/dt);
  const v=new Float32Array(N).fill(vRest),g=new Float32Array(N),refr=new Int32Array(N),counts=new Uint32Array(N);
  const isStim=new Uint8Array(N); const stim=p.stim; for(const i of stim) isStim[i]=1;
  const silenced=new Uint8Array(N); for(const i of (p.silence||[])) silenced[i]=1;
  const pStim=p.rate*dt/1000;
  const inSet=new Uint8Array(N); let act=new Int32Array(N),nAct=0;
  const pending=[]; for(let i=0;i<delaySteps;i++) pending.push([]);
  const nSc=p.nSc; let win=new Uint32Array(nSc),winSpk=[];
  const winMark=new Uint8Array(N);
  let spkNow=[];
  for(let step=0;step<steps;step++){
    const slot=step%delaySteps; const arriving=pending[slot];
    for(let a=0;a<arriving.length;a++){ const pre=arriving[a]; if(silenced[pre]) continue;
      for(let k=indptr[pre],e=indptr[pre+1];k<e;k++){ const post=indices[k]; g[post]+=w[k]*wSyn; if(!inSet[post]){inSet[post]=1;act[nAct++]=post;} } }
    spkNow=[]; let m=0;
    for(let a=0;a<nAct;a++){ const i=act[a];
      if(refr[i]<=step){ v[i]=vRest+(v[i]-vRest)*dm+g[i]*gain; g[i]*=ds;
        if(v[i]>vTh&&!isStim[i]){ v[i]=vRest; g[i]=0; refr[i]=step+refrSteps; spkNow.push(i); }
        if(Math.abs(v[i]-vRest)<1e-3&&Math.abs(g[i])<1e-3){ inSet[i]=0; continue; } }
      else { g[i]*=ds; }
      act[m++]=i; }
    nAct=m;
    for(let s=0;s<stim.length;s++){ if(Math.random()<pStim){ const i=stim[s]; v[i]=vRest; g[i]=0; refr[i]=step+refrSteps; spkNow.push(i); } }
    for(const i of spkNow){ counts[i]++; win[p.sc[i]]++; if(!winMark[i]){winMark[i]=1;winSpk.push(i);} }
    pending[slot]=spkNow;
    if((step+1)%100===0){ for(const i of winSpk) winMark[i]=0;
      postMessage({type:'win',t:(step+1)*dt,win,spk:new Uint32Array(winSpk)}); win=new Uint32Array(nSc); winSpk=[]; }
  }
  const rates=new Float32Array(N); for(let i=0;i<N;i++) rates[i]=counts[i]/(p.tRun/1000);
  postMessage({type:'done',rates},[rates.buffer]);
}
onmessage=e=>{ const d=e.data;
  if(d.type==='load'){ const b=parse(d.buf); postMessage({type:'ready',b}); }
  else if(d.type==='run'){ run(d); } };
