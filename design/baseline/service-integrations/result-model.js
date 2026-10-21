// Result fields shown by the value picker; these are design contract examples.
(function () {
  window.StepResults=step=>{
    if(!step)return[];
    if(step.kind==='each')return[['items','iterationResults','list'],['errors','iterationErrors','list']];
    if(step.kind==='parallel')return[['branches','parallelResults','object']];
    if(step.kind==='nested')return[['sent','nestedSuccess','boolean']];
    if(step.kind!=='action')return[['done','stepCompleted','boolean']];
    if(['lead','deal'].includes(step.operation))return[['id','recordId','text']];
    if(step.operation==='customer')return[['customer','paramCustomer','object']];
    return[['done','stepCompleted','boolean']];
  };
})();
