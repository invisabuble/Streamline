import { media_container } from "./handler.js"
import { media } from "./handler.js";
import { movie } from "./handler.js";
import { season } from "./handler.js";

console.log("Streamline.js loaded!");

const host = "http://streamline.local:8080"

// Redirect scrolling to horizontal for use with the mouse wheel.
document.querySelectorAll('media_group').forEach(media_group => {
  media_group.addEventListener('wheel', (e) => {
    // Let episodes lists handle their own vertical scroll natively.
    if (e.target.closest('episodes')) {
      return;
    }

    if (e.deltaY !== 0) {
      e.preventDefault();
      media_group.scrollLeft += e.deltaY;
    }
  });
});

// Prevent clicks inside the expanded content from closing the card.
document.querySelectorAll('media_content').forEach(content_element => {
  content_element.addEventListener('click', (e) => {
    e.stopPropagation();
  });
});

// Add the expansion/retraction toggle to all media divs.
document.querySelectorAll('media').forEach(media_element => {
  media_element.addEventListener('click', () => {
    const wasExpanded = media_element.classList.contains('expanded');

    // Close any other open cards first.
    document.querySelectorAll('media.expanded').forEach(el => {
      el.classList.remove('expanded');
    });

    // If the clicked card wasn't already open, open it now.
    if (!wasExpanded) {
      media_element.classList.add('expanded');
    }
  });
});

// Get the list of devices from the backend.
async function get_route(route) {
    const response = await fetch(`${host}/api/${route}`);
    return await response.json()
}

// Main streamline method.
async function streamline () {

    // Get the devices and files from the API.
    const devices = await get_route("devices");
    const files   = await get_route("get_file_list");

    const selector = document.getElementById("devices");

    for (const [ip, device] of Object.entries(devices)) {
        const option = document.createElement("option");
        option.value = ip;
        option.textContent = device.device_info.friendlyName || ip;
        selector.appendChild(option);
    }

    for (const root of files) {
        for (const folder of root.Info.Children) {
            console.log(folder);
        }
    }

}

streamline();

