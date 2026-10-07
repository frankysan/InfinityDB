const fs = require('fs');
const vm = require('vm');
const [renderer, input] = process.argv.slice(2);
class Node {
  constructor(tag='text', text='') { this.tag=tag; this._text=text; this.children=[]; this.className=''; this.classList={add(){}}; }
  set textContent(value){this._text=String(value); this.children=[];}
  get textContent(){return this._text+this.children.map(x=>x instanceof Node?x.textContent:String(x)).join('');}
  append(...items){this.children.push(...items);}
  querySelector(){return this;}
}
const document={createElement:t=>new Node(t),createTextNode:t=>new Node('text',t)};
function appendMaintainedText(node,tokens,fallback){node.append(new Node('text',tokens?.map(t=>t.label||t.text||'').join('')||fallback||''));}
const context={document,appendMaintainedText,maintainedTextFragment:tokens=>{const n=new Node();appendMaintainedText(n,tokens,'');return n;},skillCategoryBadge:c=>new Node('text',c.name),tableViewport:t=>t,Array,Set,Map,Number};
vm.createContext(context);
let code=fs.readFileSync(renderer,'utf8').replace(/^import .*;$/gm,'').replace(/export function /g,'function ');
vm.runInContext(code,context);
const data=JSON.parse(fs.readFileSync(input,'utf8'));
const skills=data.skills.map(skill=>context.rulesReferenceArticle(skill).textContent);
const specialist=context.rulesReferenceArticle(data.specialist).textContent;
console.log(JSON.stringify({skills,specialist}));
