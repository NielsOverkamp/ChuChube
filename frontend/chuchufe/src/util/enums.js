export const MessageTypes = {
    STATE: "STATE",
    LIST_OPERATION: "LIST_OPERATION",
    MEDIA_ACTION: "MEDIA_ACTION",
    SONG_END: "SONG_END",
    PLAYER_ENABLED: "PLAYER_ENABLED",
    OBTAIN_CONTROL: "OBTAIN_CONTROL",
    RELEASE_CONTROL: "RELEASE_CONTROL",
    SEARCH: "SEARCH",
    SEARCH_ID: "SEARCH_ID"
}

export const ListOperationTypes = {
    ADD: "ADD",
    DEL: "DEL",
    MOVE: "MOVE",
}


export const MediaAction = {
    PLAY: "PLAY",
    PAUSE: "PAUSE",
    NEXT: "NEXT",
    PREVIOUS: "PREVIOUS",
    REPEAT: "REPEAT",
    SHUFFLE: "SHUFFLE",
}


export const PlayerState = {
    PLAYING: "PLAYING",
    PAUSED: "PAUSED",
    LIST_END: "LIST_END",
}

export const YoutubeResourceType = {
    VIDEO: "youtube#video",
    PLAYLIST: "youtube#playlist",
    CHANNEL: "youtube#channel",
}

export const YoutubePlayerState = {
    UNSTARTED: -1,
    ENDED: 0,
    PLAYING: 1,
    PAUSED: 2,
    BUFFERING: 3,
    VIDEO_CUED: 5,
}
