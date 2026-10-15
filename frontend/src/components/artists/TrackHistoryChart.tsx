import { useEffect, useState } from 'react';
import * as am4core from '@amcharts/amcharts4/core';
import * as am4charts from '@amcharts/amcharts4/charts';
import am4themes_animated from '@amcharts/amcharts4/themes/animated';
import { ApiError, getTrack, UNREACHABLE_MESSAGE } from '../../api/client';
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
 * Unlike the Tracks radar chart and the Trends line chart, which build their
 * amCharts instance in the render body and leave it undisposed, this one
 * builds it inside an effect keyed on the Spotify id and disposes it in the
 * effect's cleanup. The chart outlives no selection: picking a different
 * track row disposes the previous instance before the new one is built, so
 * the host element never accumulates axes, series or a second chart.
 *
 * The request behind the chart is this component's own, so its failure is too:
 * a rejected `getTrack` leaves the host empty and renders the reason above it,
 * in the copy the panels use, rather than reporting the failure upwards and
 * disturbing the search results the user is still reading.
 */
export default function TrackHistoryChart(props: TrackHistoryChartProps): JSX.Element {
  const { spotifyId } = props;

  // The failure of this component's own `getTrack` request, rendered above the
  // host rather than lifted to the container.
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let chart: am4charts.XYChart | null = null;
    let cancelled = false;

    /*
     * The handle on this selection's request. Without it the rank-history call
     * runs to completion for every track the user leaves behind — and for the
     * one on screen when the panel unmounts — transferring and parsing a body
     * whose result `cancelled` throws away. The cleanup aborts it; an abort
     * rejects with no response, which is the response-less branch already
     * handled below, and `cancelled` keeps that branch from reporting it.
     */
    const controller = new AbortController();

    async function draw(): Promise<void> {
      let appearances: Track[];

      // A new request clears the previous failure, so a later selection never
      // reads a message that belonged to an earlier one.
      setError(null);

      try {
        appearances = await getTrack(spotifyId, controller.signal);
      } catch (err) {
        // The host element stays empty and the message above it says why,
        // instead of leaving the region blank as though the request were still
        // in flight. A failure that carried a response names itself through the
        // client's `ApiError` status text; one that never reached the API has no
        // text of its own, so it shows the client's shared copy for that case.
        // Returning here also keeps the rejection inside this function, so
        // nothing reaches the window as an unhandled rejection. A reply that
        // arrives after this effect was cleaned up belongs to a selection that is
        // already gone, so it is dropped rather than overwriting the live one.
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : UNREACHABLE_MESSAGE);
        }
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

      // A line is painted along its points, so a history of exactly one
      // appearance has a path of zero length and the host stays visually empty.
      // The bullet is the mark that sits on a point itself, which is what makes
      // a single-appearance selection visible; it is pushed for every
      // appearance rather than special-cased for that one, and it is filled in
      // the series' own accent so the mark reads as part of the line.
      // A chart mark is not a control, so the mark and its series both opt out
      // of the library's focusable-item rule: left to itself it makes a small
      // series' bullets keyboard-focusable once the data validates, one
      // nameless stop per point and no focus indicator.
      series.skipFocusThreshold = 1;
      const bullet = new am4charts.CircleBullet();
      bullet.focusable = false;
      bullet.circle.fill = am4core.color('rgb(128, 103, 220)');
      series.bullets.push(bullet);
    }

    void draw();

    return () => {
      cancelled = true;
      controller.abort();
      chart?.dispose();
    };
  }, [spotifyId]);

  return (
    <>
      {/* The house error marker — the shared `.error` text the panels render —
          sits above the host, which keeps its id and its inline style untouched:
          a failed request leaves the chart region as it is and states the failure
          in the space above it. The class sits on a wrapper rather than on the
          heading, because the shared stylesheet rule centres an `h1` that is
          inside `.error`. */}
      {error !== null && (
        <div className='error'>
          <h1>{error}</h1>
        </div>
      )}
      <div
        id={CHART_ID}
        style={{
          width: '100%',
          height: '260px',
          marginTop: '10px',
          marginRight: '20px'
        }}
      />
    </>
  );
}
