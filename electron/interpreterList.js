const fs = require('node:fs')

const interpreterList = () => 
	fs.readFileSync(".interpreter_list", 'utf8')
		.split('\n')
		.map((line) => ({ location: line.slice(1), using: line.charAt(0) == 'O' }))

const updateList = (list) => {
	fs.writeFileSync(
		".interpreter_list", 
		list.map((item) => `${item.using ? 'O' : 'X'}${item.location}`).join('\n')
	);
}

const addInterpreter = (loc) => {
	let list = interpreterList()
	list.push({ location: loc, using: false })
	updateList(list)

	return list
}

const select = (loc) => {
	let list = interpreterList()
	for (let i = 0; i < list.length; i++) {
		list[i].using = (list[i].location === loc)
	}
	updateList(list)

	return list
}

const currentInterpreter = () => {
	return interpreterList().find((interpreter) => interpreter.using)
}

module.exports = { interpreterList, addInterpreter, select, currentInterpreter }