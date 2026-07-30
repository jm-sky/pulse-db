// date + hour:minute
export const smallDateTime = (date: string) => {
  return `${new Date(date).toLocaleDateString()} ${new Date(date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
}
