import { Container, getContainer } from "@cloudflare/containers";

export class Speech2TextContainer extends Container {
  defaultPort = 8080;
  sleepAfter = "10m";

  envVars = {
    OPENAI_API_KEY: this.env.OPENAI_API_KEY ?? "",
    GOOGLE_API_KEY: this.env.GOOGLE_API_KEY ?? "",
    GEMINI_API_KEY: this.env.GEMINI_API_KEY ?? "",
    ELEVENLABS_API_KEY: this.env.ELEVENLABS_API_KEY ?? "",
  };
}

export default {
  async fetch(request, env) {
    return getContainer(env.SPEECH2TEXT_CONTAINER).fetch(request);
  },
};
