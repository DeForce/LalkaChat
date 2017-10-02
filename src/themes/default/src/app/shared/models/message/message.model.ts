import { Emote } from './emote.model';
import { Platform } from './platform.model';
import { Badge } from './badge.model';
import { MessageType } from './message.type';
import { CommandType } from './command.type';

export interface Message {
  id: string;
  me: boolean;
  pm: boolean;
  mention: boolean;
  platform: Platform;
  emotes: Array<Emote>;
  badges: Array<Badge>;
  levels?: any;
  nick_colour: string;
  channel_name: string;
  text: string;
  type: MessageType;
  command: CommandType;
  user: string;
  unixtime: number;
}
