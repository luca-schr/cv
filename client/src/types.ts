export type Lang = "fr" | "en";

export type Localized = {
  fr?: string;
  en?: string;
};

export type ProfileSummary = {
  id: string;
  profile: Localized;
};

export type ProfileDetail = {
  id: string;
  lang: Lang;
  title: string;
  profile: Localized;
  markdown: string;
};

export type LoadStatus = "loading" | "ok" | "error";

export type NamingOpts = {
  title: string;
  english: boolean;
};
