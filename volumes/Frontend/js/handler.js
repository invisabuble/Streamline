// handler.js

function classify_entry(entry) {
  // Case 1: the entry IS a file directly (e.g. Obsession/media.mp4).
  if (entry.Info.Type === "File") {
    return "movie";
  }

  // Otherwise it's a directory — check how many files sit inside it.
  const fileChildren = entry.Info.Children.filter(c => c.Info.Type === "File");

  // One file inside → treat as a single movie (e.g. a Harry Potter film folder).
  if (fileChildren.length <= 1) {
    return "movie";
  }

  // Multiple files inside → treat as a season.
  return "season";
}

export class media_container {
  constructor (container_json, host) {

    this.container_json = container_json;
    this.host = host;
    this.media_title = container_json.Name;

    // Create the media container elements.
    this.element = document.createElement("media_container");
    this.element.innerHTML = `<media_group_title class="media_content_text">${this.media_title}</media_group_title>`;
    this.media_group = document.createElement("media_group");
    this.element.appendChild(this.media_group);

    this.children = container_json.Info.Children;

    for (const media_json of this.children) {
      const type = classify_entry(media_json);
      let card;

      if (type === "movie") {
        const fileNode = media_json.Info.Type === "File"
          ? media_json
          : media_json.Info.Children.find(c => c.Info.Type === "File");

        const has_prefix = media_json.Info.Type !== "File";
        const title = has_prefix ? media_json.Name.slice(3) : this.media_title;
        const icon_url = `${this.host}/mnt/${encodeURI(fileNode.Info.Icon)}`;

        card = new movie(this.host, this.media_title, icon_url, title, fileNode.Path);
      }
      else {
        const title = media_json.Name.slice(3);
        const icon_url = `${this.host}/mnt/${encodeURI(media_json.Info.Children[0].Info.Icon)}`;
        card = new season(this.host, this.media_title, icon_url, title, media_json.Info.Children);
      }

      this.media_group.appendChild(card.media);
    }

    document.getElementById("content").appendChild(this.element);
  }
}

export class media {
  constructor (host, media_title, img, title) {
    this.host = host;
    this.media_title = media_title;
    this.title = title;

    this.media = document.createElement("media");
    this.media_card = document.createElement("media_card");
    this.media_card.innerHTML = `<img src="${img}">`;
    this.media_content = document.createElement("media_content");
    this.media_content.innerHTML = `<media_title class="media_content_text">${title}</media_title>`;
    this.media_desc = document.createElement("media_desc");
    this.media_desc.classList.add("media_content_text");

    this.media_content.appendChild(this.media_desc);
    this.media.appendChild(this.media_card);
    this.media.appendChild(this.media_content);
  }

  create_play_media (Path, Text = "Play") {
    const play_media = document.createElement("play_media");
    play_media.textContent = Text;
    play_media.dataset.path = Path;

    play_media.addEventListener("click", (event) => {
      if (Text == "Play") {
        this.play_media_file(event.currentTarget.dataset.path);
      } else {
        this.play_media_file(event.currentTarget.dataset.path, Text);
      }
    });

    return play_media;
  }

  async play_media_file (media_path, episode_name = "") {

    const device = document.getElementById("selector").value;
    if (device == "No AV Devices Found") {
      console.log(device);
    }

    let media_title = `${this.media_title} : ${this.title}`;
    
    if (episode_name != "") {
      media_title += ` : ${episode_name}`;
    }

    const params = new URLSearchParams({
      file  : media_path,
      device: device,
      title : media_title
    });

    const route = `${this.host}/api/set_target?${params.toString()}`;
    const play_ = `${this.host}/api/play_target?device=${device}&speed=1`;
    
    await fetch(route);
    await fetch(play_);

    console.log(route);
  }
}

export class movie extends media {
  constructor (host, media_title, img, title, media_path) {
    super(host, media_title, img, title);
    this.media_path = media_path;

    this.media_desc.textContent = "Two gay retards go munting together."
    
    const play_media = this.create_play_media(this.media_path);
    this.media_desc.appendChild(play_media);
  }
}

export class season extends media {
  constructor (host, media_title, img, title, episode_files) {
    super(host, media_title, img, title);
    this.media_desc.textContent = "Another season of munting..."
    
    // Iterate through the episodes creating the play media elements for each episode.
    this.episodes = episode_files;
    const episodes = document.createElement("episodes");
    for (const episode of episode_files) {

      const play_media = this.create_play_media(episode.Path, episode.Name.slice(0, -4));
      episodes.appendChild(play_media);

    }

    // Append the episodes list to the media description.
    this.media_desc.appendChild(episodes);
  
  }
}