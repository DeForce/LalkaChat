<!DOCTYPE HTML>
<html>
    <head>
        <title>Lalka - chat</title>
        <meta charset="UTF-8"/>
        <meta http-equiv="X-UA-Compatible" content="IE=Edge" />

        <link rel="stylesheet" type="text/css" href="css/style.css" />
    </head>

    <body>
        <div id="chat-container">
            <transition-group name="message">
            <div class="message_shared"
                 v-for="message in messages"
                 v-bind:style="style_message"
                 :class="[message.type, { message_old: message.old }]"
                 :key="message.id"
                 @mouseenter="mouseenter(message)" @mouseleave="mouseleave(message)">
                <div class="message-remove" v-if="message && message.deleteButton">
                    <img class="delete" @click="remove(message)" :src="'img/gui/delete.png'" />
                </div>

                <div class="message-source">
                    <img class="platform" :src="message.platform.icon || 'img/sources/' + message.platform.id + '.png'" />
                </div>

                <template v-if="message.show_channel_name">
                    <div v-bind="style_text" class="channel">[{{message.channel}}]</div>
                </template>

                <div class="message-badges" v-for="badge in message.badges">
                    <img class="badge" :src="badge.url" :class="'badge-' + badge.badge" />
                </div>

                <div v-bind="style_text" class="username" :style="{color: message.username_color}">{{ message.username }}</div>
                <template v-if="!message.me">
                    <div v-bind="style_text">:</div>
                </template>
                <div v-bind="style_text" class="text" v-html="sanitize(message)" :class="{ 'private': message.pm, 'mention': message.mention }"></div>
            </div>
            </transition-group>
        </div>
    </body>
</html>
