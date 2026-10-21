// Keep the real DecisionDialog inside its x-dc frame, including in the all-frames view.
// The product component and its visual styles are unchanged.
(function () {
  const { h }=window.ServiceParts,U=window.ServiceUI,R=window.React;
  window.CanvasDialog=function Dialog(props){
    const marker=R.useRef(null),[container,setContainer]=R.useState(null);
    R.useLayoutEffect(()=>setContainer(marker.current.closest('.si-screen')),[]);
    return h(R.Fragment,null,h('span',{ref:marker,hidden:true}),container && h(U.ConfigProvider,{getPopupContainer:()=>container},h(U.DecisionDialog,props)));
  };
})();
