import { useEffect } from 'react';
import * as am4core from '@amcharts/amcharts4/core';
import * as am4charts from '@amcharts/amcharts4/charts';
import am4themes_animated from '@amcharts/amcharts4/themes/animated';
import { getTrack } from '../../api/client';
import type { Track } from '../../types/api';

am4core.useTheme(am4themes_animated);

interface TrackHistoryChartProps {
  spotifyId: string;
}

const CHART_ID = 'trackHistoryChart';
const lightWhite = 'rgb(230, 230, 230)';

/**
 * Order two appearances by chart week, oldest first.
 *
 * `week` is one of the nullable `tracks` columns the serializer reports as a
 * JSON `null`, so an appearance without one is ordered before the dated ones:
 * it has no position in time of its own, and holding the dateless points at one
 * end leaves the dated ones in the single uninterrupted run the line reads as.
 * Between two dated appearances this is exactly the text comparison the ISO
 * `YYYY-MM-DD` form already orders as date order.
 */
function byWeekAscending(a: Track, b: Track): number {
  if (a.week === null) {
    return b.week === null ? 0 : -1;
  }
  if (b.week === null) {
    return 1;
  }
  if (a.week < b.week) {
    return -1;
  }
  if (a.week > b.week) {
    return 1;
  }
  return 0;
}

/**
 * One selected track's chart history, drawn as rank over time.
 *
 * Rank 1 is the best position, so the value axis is inverted: the line rises
 * towards the top of the chart as the track climbs, exactly as a chart reader
 * expects, and rank 100 sits at the bottom.
 *
 * Unlike the two older charts, which build their amCharts instance in the
 * render body and leave it undisposed, this one builds it inside an effect
 * keyed on the Spotify id and disposes it in the effect's cleanup. The chart
 * outlives no selection: picking a different track row disposes the previous
 * instance before the new one is built, so the host element never accumulates
 * axes, series or a second chart.
 */
export default function TrackHistoryChart(props: TrackHistoryChartProps): JSX.Element {
  const { spotifyId } = props;

  useEffect(() => {
    let chart: am4charts.XYChart | null = null;
    let cancelled = false;

    async function draw(): Promise<void> {
      let appearances: Track[];

      try {
        appearances = await getTrack(spotifyId);
      } catch {
        // Leaving the host element empty is this component's whole response to a
        // failed request: the panel that renders it owns the error message, and
        // this component receives no error channel to report through. Returning
        // here also keeps the rejection inside this function, so nothing reaches
        // the window as an unhandled rejection.
        return;
      }

      // The endpoint answers rank-ordered, which is the wrong order for a series
      // that reads left to right in time. `week` is an ISO `YYYY-MM-DD` string,
      // so comparing it as text is date order.
      const history = [...appearances].sort(byWeekAscending);

      // A request that resolved after this effect was cleaned up would otherwise
      // build a chart into a host element React has already moved on from.
      if (cancelled) {
        return;
      }

      const created = am4core.create(CHART_ID, am4charts.XYChart);
      chart = created;

      created.data = history;
      created.dateFormatter.inputDateFormat = 'yyyy-MM-dd';
      created.dateFormatter.dateFormat = 'yyyy-MM-dd';

      const dateAxis = created.xAxes.push(
        new am4charts.DateAxis<am4charts.AxisRendererX>()
      );
      dateAxis.renderer.grid.template.stroke = am4core.color(lightWhite);
      dateAxis.renderer.labels.template.fontSize = 11;
      dateAxis.renderer.labels.template.fill = am4core.color(lightWhite);
      dateAxis.renderer.labels.template.fillOpacity = 0.8;

      const valueAxis = created.yAxes.push(
        new am4charts.ValueAxis<am4charts.AxisRendererY>()
      );
      valueAxis.renderer.inversed = true;
      valueAxis.min = 1;
      valueAxis.max = 100;
      valueAxis.strictMinMax = true;
      valueAxis.renderer.grid.template.stroke = am4core.color(lightWhite);
      valueAxis.renderer.labels.template.fontSize = 11;
      valueAxis.renderer.labels.template.fill = am4core.color(lightWhite);
      valueAxis.renderer.labels.template.fillOpacity = 0.8;

      const series = created.series.push(new am4charts.LineSeries());
      series.dataFields.dateX = 'week';
      series.dataFields.valueY = 'rank';
      series.strokeWidth = 2;
      series.tensionX = 0.8;
      series.stroke = am4core.color('rgb(128, 103, 220)');
    }

    void draw();

    return () => {
      cancelled = true;
      chart?.dispose();
    };
  }, [spotifyId]);

  return (
    <div
      id={CHART_ID}
      style={{
        width: '100%',
        height: '260px',
        marginTop: '10px',
        marginRight: '20px'
      }}
    />
  );
}
