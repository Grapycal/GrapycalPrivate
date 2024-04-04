import { EventTopic, IntTopic, StringTopic } from "objectsync-client"
import { Control } from "./control"
import { print } from "../../devUtils"
import { BindInputBoxAndTopic } from "../../ui_utils/interaction"
import { TextBox} from "../../utils"
import {basicSetup, EditorView} from "codemirror"
import {autocompletion, CompletionResult, Completion, CompletionContext} from "@codemirror/autocomplete"

export class CodeControl extends Control {

    editorView: EditorView
    text = this.getAttribute("text", StringTopic)
    label = this.getAttribute("label", StringTopic)
    editable = this.getAttribute("editable", IntTopic)
    placeholder = this.getAttribute("placeholder", StringTopic)

    protected template = `
    <div class="control flex-horiz" id="codecontrol">
        <div class="label" id="label"></div>
    </div>
    `

    protected css: string = `
        #codecontrol {
            overflow: visible;
        }
        .label{
            flex-shrink: 0;
            min-width: 0px;
        }
        .cm-editor {
            resize: "vertical";
            overflow: "hidden";
            min-height: "500px";
            min-width: "800px";
        }
        .cm-editor:has(.cm-tool-tip-autocomplete) {
            overflow: "visible";
        }
    `

    // private handleResponse(response: CompletionItem[]) => Compl{
    //     completions = response
    //     this.editorView.dispatch({effects: autocompletion({override: [myCompletions], closeOnBlur: false})})

    // }

    // private async myCompletions(context: any) {
    //     let before = context.matchBefore(/\w+/)
    //     // If completion wasn't explicitly started and there
    //     // is no word before the cursor, don't open completions.
    //     if (!context.explicit && !before) return null
    //     this.makeRequest('suggestions', {text: context},
    //     return {
    //         from: before ? before.from : context.pos,
    //         options: completions,
    //         validFor: /^\w*$/
    //     }
    // }

    private async myCompletions(context: CompletionContext): Promise<CompletionResult> {
        const promise = new Promise<CompletionResult>((resolve, reject) => {
            const text = context.matchBefore(/[^\n]*/)
            this.makeRequest('suggestions', {text: text}, (response: Completion[]) => {
                const completions = response
                // debugger
                resolve({
                    from: context.pos,
                    options: completions,
                    validFor: /^\w*$/
                })
            })
        })
        return promise
    }


    protected onStart(): void {
        super.onStart()
        this.myCompletions = this.myCompletions.bind(this)
        this.editorView =  new EditorView({
          doc: "// Type a 'p'\n",
          extensions: [
            basicSetup,
            autocompletion({override: [this.myCompletions], closeOnBlur: false})
          ],
          parent: this.htmlItem.baseElement
        })

        // this.editorView.from
        this.editorView.dom.addEventListener("mousedown", (e) => {
            e.stopPropagation()
        })
        // consume a scroll event
        this.editorView.dom.addEventListener("wheel", (e) => {
            e.stopPropagation()
        })
    }


}


// let completions: Completion[] = [
//   {label: "panic", type: "keyword"},
//   {label: "park", type: "constant", info: "Test completion"},
//   {label: "password", type: "variable"},
// ]
