import { HtmlItem } from "../component/htmlItem"
import { Node } from "../sobjects/node"
import { ExposedAttributeInfo } from '../inspector/inspector'
import { Workspace } from "../sobjects/workspace"
import { Inspector } from "../inspector/inspector"
import { Componentable } from "../component/componentable"
import { Marked } from '@ts-stack/markdown';


export function object_equal(a:any,b:any){
    return JSON.stringify(a) === JSON.stringify(b);
}

export class NodeInspector extends Componentable{
    static instance: NodeInspector;
    private inspector: Inspector
    nodes: Node[] = []
    protected get template(): string {return `
        <div ref="baseEl" class="full-height flex-vert">
            <div id="node_info">
                <div ref="nodeTypeDiv"></div>
                <div ref="extensionNameDiv"></div>
                <div ref="nodeDescriptionDiv"></div>
            </div>
            <hr>
            <div slot="Inspector"></div>
            <hr>
            <div ref="outputDisplayDiv"></div>
            <button ref="clearOutputButton">Clear Output</button>
        </div>
        `;
    }

    protected get style(): string {return `
        #extension_name{
            color: var(--text-low);
        }
        
    `}

    nodeTypeDiv: HTMLElement;
    extensionNameDiv: HTMLElement;
    nodeDescriptionDiv: HTMLElement;
    outputDisplayDiv: HTMLElement;
    clearOutputButton: HTMLElement;

    sidebarEl: HTMLElement;
    baseEl: HTMLElement;

    constructor(parent: HtmlItem){
        super()
        NodeInspector.instance = this;
        this.inspector = new Inspector()
        this.inspector.mount(this)
        this.sidebarEl = parent.baseElement as HTMLElement;
        this.clearOutputButton.onclick = ()=>{
            if(this.nodes.length === 1){
                this.nodes[0].output.set([])
            }
            this.outputDisplayDiv.innerText = '';
        }

        this.outputDisplayDiv.style.bottom = '0px';
        this.sidebarEl.style.display = 'none';
        this.baseEl.style.alignItems = 'stretch'
        
    }

    addNode(node: Node){
        this.nodes.push(node);
        this.updateContent();
    }
    
    removeNode(node: Node){
        let index = this.nodes.indexOf(node);
        if(index === -1) throw new Error('node not found');
        this.nodes.splice(index,1);
        this.updateContent();
    }


    private updateContent(){
        this.updateNodeInfo();
        this.updateHierarchy();
    }
    
    private updateNodeInfo(){
        
        this.outputDisplayDiv.innerText = '';
    
        if(this.nodes.length === 0){
            this.sidebarEl.style.display = 'none';
            return;
        }else{
            this.sidebarEl.style.display = 'flex';
        }
        this.linker.unlink(this.addOutput,false)
        this.linker.unlink(this.onOutputSet,false)
        if(this.nodes.length === 1){
            let fullType = this.nodes[0].type_topic.getValue();
            let type = fullType.split('.')[1];
            let extensionName = fullType.split('.')[0];
            this.nodeTypeDiv.innerText = type;
            this.extensionNameDiv.innerText = extensionName;
            
            let outputAttribute = this.nodes[0].output;
            for(let item of outputAttribute.getValue()){
                this.addOutput(item);
            }
            this.linker.link(outputAttribute.onInsert,this.addOutput);
            this.linker.link(outputAttribute.onSet,this.onOutputSet);
            
        }
        else{//multiple nodes
            let nodeTypeString = '';
            if (this.nodes.length <3){
                for(let node of this.nodes){
                    nodeTypeString += node.type_topic.getValue().split('.')[1] + ', ';
                }
                nodeTypeString = nodeTypeString.slice(0,-2);
            }
            else{
                nodeTypeString = `${this.nodes.length} nodes`
            }
            this.nodeTypeDiv.innerText = nodeTypeString;
            this.extensionNameDiv.innerText = '';
        }
        // if all nodes have the same description, display it
        const node_types_topic = Workspace.instance.nodeTypesTopic
        let description = ''
        for(let node of this.nodes){
            let nodeType = node.type_topic.getValue()
            let nodeTypeDescription = node_types_topic.get(nodeType).description
            if(description === ''){
                description = nodeTypeDescription
            }else{
                if(description !== nodeTypeDescription){
                    description = ''
                    break
                }
            }
        }
        // const markdownDescription = marked(description);
        // const descriptionString = String(description).replace("\n", "<br/>")
        // const descriptionString = String(description)
        if (description === null) {
            description = '**This node has no description.**'
        }
        const markdownDescription = Marked.parse(description);
        this.nodeDescriptionDiv.innerHTML = markdownDescription
    }
    
    private addOutput(item:[string,string]){
        let [type,content] = item;
        if(content === '') return;
    
        //replace space
        content = content.replace(/ /g,'\u00a0');
    
        let span = document.createElement('span');
        span.classList.add('output-item');
        span.innerText = content;
        if (type === 'error'){
            span.classList.add('error');
        }else{
            span.classList.add('output');
        }
        this.outputDisplayDiv.appendChild(span);
    }
    
    private onOutputSet(value:any[]){
        if(value.length === 0)
            this.outputDisplayDiv.innerText = '';
    }
    
    private updateHierarchy(){
        
        // group by display_name
        let exposedAttributes = new Map<string,ExposedAttributeInfo[]>();
        for(let node of this.nodes){
            for(let info of node.exposed_attributes.getValue()){
                if(!exposedAttributes.has(info.display_name)){
                    exposedAttributes.set(info.display_name,[]);
                }
                exposedAttributes.get(info.display_name).push(info);
            }
        }
        
        this.inspector.update(exposedAttributes,this.nodes.length);
    }
    
}



