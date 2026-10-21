/**
 * Renders a DOM node (the results report) to a multi-page PDF, preserving
 * charts and layout by rasterizing the node rather than re-typesetting it.
 */
export async function exportReportPdf(node: HTMLElement, fileName: string): Promise<void> {
  // Loaded on demand: together they are most of the bundle and only needed when a report is exported.
  const [{ jsPDF }, { default: html2canvas }] = await Promise.all([import('jspdf'), import('html2canvas')]);

  const canvas = await html2canvas(node, {
    backgroundColor: '#0a0a0c',
    scale: 2,
    useCORS: true,
  });

  const imgData = canvas.toDataURL('image/png');
  // Page sized to exactly fit the rasterized report, so it renders as one
  // continuous page rather than being sliced across arbitrary page breaks.
  const pdf = new jsPDF({ orientation: 'portrait', unit: 'px', format: [canvas.width, canvas.height] });

  pdf.addImage(imgData, 'PNG', 0, 0, canvas.width, canvas.height);
  pdf.save(fileName);
}
