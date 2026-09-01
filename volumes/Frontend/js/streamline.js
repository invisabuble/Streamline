console.log('Loaded index.js!');

const host = "http://streamline.local:8080"

async function get_route(route) {
  const response = await fetch(`${host}/api/${route}`);
  return await response.json()
}

function attach_behaviors () {
    // Enable horizontal scrolling for the series groups.
    document.querySelectorAll('series').forEach(media_group => {
        media_group.addEventListener('wheel', (e) => {
            if (e.target.closest('episode')) return;

            const overflowing = media_group.scrollWidth > media_group.clientWidth;

            if (!overflowing || e.deltaY === 0) return;

            const atLeft = media_group.scrollLeft <= 0;
            const atRight =
                media_group.scrollLeft + media_group.clientWidth >= media_group.scrollWidth;

            // Scrolling down/right
            if (e.deltaY > 0 && !atRight) {
                e.preventDefault();
                media_group.scrollLeft += e.deltaY;
            }

            // Scrolling up/left
            else if (e.deltaY < 0 && !atLeft) {
                e.preventDefault();
                media_group.scrollLeft += e.deltaY;
            }
        });
    });
}

// Base class for creating a media object.
class media {
    constructor (data, parent) {
        
        this.icon = data.Icon;
        this.media = data.Media;
        this.name = data.Name;

        console.log(this.media);

        this.media_element = document.createElement("media");

        this.media_card = document.createElement("media_card");
        this.play_media = document.createElement("play_media");

        // Populate play media element.
        if (Array.isArray(this.media)) {
            // If the media is an array then generate the episode list.
            this.play_media.setAttribute("class", "series");
            this.play_media.innerHTML = `<series_title class="title_text">${this.name}</series_title>`;
            for (const episode of this.media) {
                const ep_element = document.createElement("episode");
                ep_element.setAttribute("class", "title_text");
                ep_element.innerText = episode.Name;

                ep_element.addEventListener("click", (e) => {
                    this.play_media_file(episode.Path, episode.Name);
                });

                this.play_media.appendChild(ep_element);
            }
        } else {
            // If its not an array add the play svg.
            this.play_media.innerHTML = "<img src='./image/play.svg'>"
            this.play_media.addEventListener("click", (e) => {
                this.play_media_file(this.media, this.name);
            });
        }
        
        this.media_img  = document.createElement("img");
        this.media_img.setAttribute("src", `${host}/mnt/${this.icon}`);

        // Append everything together.
        this.media_card.appendChild(this.play_media);
        this.media_card.appendChild(this.media_img);
        this.media_element.appendChild(this.media_card);

        parent.appendChild(this.media_element);
    }

    async play_media_file (media_path, name = "") {

        const device = document.getElementById("selector").value;
        if (device == "No AV Devices Found") {
            console.log(device);
            return;
        }

        let media_title = `${this.name} : ${name}`;

        const params = new URLSearchParams({
            file  : media_path,
            device: device,
            title : media_title
        });

        const route = `${host}/api/set_target?${params.toString()}`;
        const play_ = `${host}/api/play_target?device=${device}&speed=1`;
        
        await fetch(route);
        await fetch(play_);

        console.log(route);
    }
    
}

class series {
    constructor (data, parent) {
        this.series = document.createElement("series");
        this.series.setAttribute("class", "series");

        for (const entry of data.Items) {
            new media(entry, this.series);
        }

        parent.appendChild(this.series);
    }
}

async function streamline () {

    const files   = await get_route("get_file_list");
    const devices = await get_route("devices");

    // If the devices list is populated then delete the no av message.
    const selector = document.getElementById("selector");
    if (Object.keys(devices).length > 0) {
        selector.innerHTML = "";
    }

    for (const [ip, device] of Object.entries(devices)) {
        console.log(ip, device);
        const option = document.createElement("option");
        option.value = ip;
        option.textContent = device.device_info.friendlyName || ip;
        selector.appendChild(option);
    }

    console.log(files);

    for (const file of files) {
        switch (file.Type) {
            case "Series" : {
                parent = document.getElementById("Series");
                new series(file, parent);
                break;
            }
            case "Movie" : {
                parent = document.getElementById("Movie");
                new media(file.Items[0], parent);
                break;
            }
        }
    }

    attach_behaviors();
}

window.addEventListener("load", async () => {
    streamline();
});