import { ComponentManager, IComponentable } from "../component/component"
import { Componentable } from "../component/componentable"
import { HtmlItem } from "../component/htmlItem"
import { Linker } from "../component/linker"
import { print } from "../devUtils"
import { Node } from "../sobjects/node"

class TwoWayMap<K,V>{
    private readonly map = new Map<K,V>();
    private readonly reverseMap = new Map<V,K>();

    set(key: K, value: V){
        this.map.set(key,value);
        this.reverseMap.set(value,key);
    }

    get(key: K): V|undefined{
        return this.map.get(key);
    }

    getReverse(value: V): K|undefined{
        return this.reverseMap.get(value);
    }

    delete(key: K){
        let value = this.map.get(key);
        this.map.delete(key);
        this.reverseMap.delete(value!);
    }

    deleteReverse(value: V){
        let key = this.reverseMap.get(value);
        this.map.delete(key!);
        this.reverseMap.delete(value);
    }

    clear(){
        this.map.clear();
        this.reverseMap.clear();
    }

    keys(){
        return this.map.keys();
    }

    values(){
        return this.map.values();
    }
}

export class HierarchyNode extends Componentable{
    protected get template(): string { return `
    <div class="hierarchy-node full-width">
        <span id="name" class="hierarchy-name"></span>
        <div id="indent" class="hierarchy-indent">
            <div slot="childnode" class="hierarchy-child-node-slot flex-vert">
                
            </div>
            <div slot="leaf" class="hierarchy-leaf-slot">
                        
            </div>
        </div>
    </div>
    `}

    private readonly children = new Map<string,HierarchyNode>();
    private readonly leafs: HtmlItem[] = [];
    private expanded = true;
    private readonly itemIdMap = new TwoWayMap<string,HtmlItem>();

    readonly name: string;
    readonly path: string;
    
    constructor(name:string,path:string='',isRoot: boolean = false){
        super();
        this.name = name;
        this.path = path;
        this.htmlItem.applyTemplate(this.template);
        if(isRoot){
            this.htmlItem.getHtmlEl('name').remove();
            this.htmlItem.getHtmlEl('indent').classList.remove('hierarchy-indent');
            this.htmlItem.baseElement.classList.remove('hierarchy-node');
        }
        if(!isRoot){
            this.htmlItem.getHtmlEl('name').innerText = name;
            this.linker.link2(this.htmlItem.getHtmlEl('name'),'mousedown',this.mouseDown);
            this.htmlItem.getHtmlEl('indent').style.display = 'block';
            for(let className of Node.getCssClassesFromCategory(path)){
                this.htmlItem.baseElement.classList.add(className);
            }
            if(path.lastIndexOf('/') === 0){
                this.htmlItem.getHtmlEl('name').classList.add('hierarchy-h1');
            }
        }
    }

    private addChild(name: string){
        let newChild = new HierarchyNode(name,this.path+'/'+name);
        this.children.set(name,newChild);
        newChild.htmlItem.setParent(this.htmlItem,'childnode')
    }

    private removeChild(name: string){
        let child = this.children.get(name);
        if(child){
            child.destroy();
            this.children.delete(name);
        }
    }

    private mouseDown(e: MouseEvent){
        e.stopPropagation();
        this.expanded = !this.expanded;
        if(this.expanded){
            this.htmlItem.getHtmlEl('name').innerText = this.name + ' ';
            this.htmlItem.getHtmlEl('indent').style.display = 'block';
        }else{
            this.htmlItem.getHtmlEl('name').innerText = this.name + ' >'
            this.htmlItem.getHtmlEl('indent').style.display = 'none';
        }
    }

    addLeaf(leaf: HtmlItem|IComponentable,path: string[]|string='',id:string=null){
        let leaf_: HtmlItem;
        if(leaf instanceof HtmlItem){
            leaf_ = leaf;
        }else{
            leaf_ = leaf.componentManager.getComponent(HtmlItem);
        }

        if(id!==null){
            this.itemIdMap.set(id,leaf_);
        }

        if(typeof path === 'string'){
            path = path.split('/')
        }
        if(path.length === 0 || path[0] === ''){
            leaf_.setParent(this.htmlItem,'leaf')
            this.leafs.push(leaf_);
        }else{
            let child = this.children.get(path[0]);
            if(!child){
                this.addChild(path[0]);
                child = this.children.get(path[0]);
            }
            child!.addLeaf(leaf_,path.slice(1));
        }
    }

    removeLeafById(id: string){
        let leaf = this.itemIdMap.get(id);
        if(leaf){
            this.removeLeaf(leaf,id);
        }else{
            throw new Error(`leaf with id ${id} not found`);
        }
    }

    removeLeaf(leaf: HtmlItem, path: string[]|string){
        if(typeof path === 'string'){
            path = path.split('/')
        }
        if(path.length === 0 || path[0] === ''){
            this.leafs.splice(this.leafs.indexOf(leaf),1);
            this.itemIdMap.deleteReverse(leaf);
        }else{
            let child = this.children.get(path[0])!;
            child.removeLeaf(leaf,path.slice(1));

            if(child.isEmpty()){
                this.removeChild(path[0]);
            }
        }
    }

    clear(){
        this.children.forEach((child)=>{
            child.destroy();
        })
        this.children.clear();
        this.leafs.forEach((leaf)=>{
            leaf.componentManager.destroy();
        })
        this.leafs.splice(0,this.leafs.length);
    }

    destroy(){
        this.componentManager.destroy();
        for (let child of this.children.values()){
            child.destroy();
        }
        for (let leaf of this.leafs){
            leaf.componentManager.destroy();
        }
    }

    isEmpty(){
        return this.children.size === 0 && this.leafs.length === 0;
    }
}