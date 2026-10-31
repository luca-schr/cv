import { useMemo } from "react";

const MONTHS_FR = [
  "janvier",
  "février",
  "mars",
  "avril",
  "mai",
  "juin",
  "juillet",
  "août",
  "septembre",
  "octobre",
  "novembre",
  "décembre",
];

const MONTHS_EN = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

function formatLastModified(value: string, english: boolean): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  const seconds = String(date.getSeconds()).padStart(2, "0");
  const day = date.getDate();
  const month = (english ? MONTHS_EN : MONTHS_FR)[date.getMonth()];
  const year = date.getFullYear();
  return `${hours}:${minutes}:${seconds} - ${day}, ${month}, ${year}`;
}

export function useLastModified(value: string | null | undefined, english: boolean): string {
  return useMemo(() => (value ? formatLastModified(value, english) : ""), [value, english]);
}
