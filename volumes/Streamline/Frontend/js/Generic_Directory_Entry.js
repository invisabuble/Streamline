class Generic_Directory_Entry {
    constructor (type, parent, title) {
        this.type = type;
        this.parent = parent;

        // Create the media entry object
        this.element = document.createElement("media_entry");

        this.icon = document.createElement("media_icon");

        // Fetch and inject the svg file
        fetch(`/svg/${type}_icon.svg`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Failed to load SVG: ${response.status}`);
                }

                return response.text();
            })
            .then(svgText => {
                this.icon.innerHTML = svgText;
            })
            .catch(error => {
                console.error(`Error loading ${type} SVG:`, error);
            });

        this.title = document.createElement("media_title");
        this.title.innerText = title;

        this.element.appendChild(this.icon);
        this.element.appendChild(this.title);

        this.parent.appendChild(this.element);
    }
}

window.Generic_Dir = Generic_Directory_Entry;