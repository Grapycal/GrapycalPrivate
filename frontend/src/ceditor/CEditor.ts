import { Action } from "objectsync-client"
import { Componentable } from "../component/componentable"

export class CEditor extends Componentable {
    public readonly onResize = new Action<[], void>()
}
