import PySimpleGUI as sg
from d3b_redcap_api.redcap import REDCapStudy
import arrow
import xlsxwriter
import re
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sg.theme("BrightColors")  # Add a little color
table_font = ("Courier New", 14)
sg.set_options(font=table_font)

fetch_status = sg.Column(
    [
        [
            sg.ProgressBar(
                k="FETCH_BAR", max_value=10, s=(20, 15), border_width=1, visible=False
            ),
            sg.Text("", k="FETCH_ERROR", s=(0, 1), visible=False),
        ]
    ],
    expand_x=True,
    pad=(0, 0),
)
fetch_button = sg.Column(
    [[sg.Button("1. Fetch Project Data", k="FETCH_BUTTON")]],
    element_justification="right",
    pad=(0, 0),
)
fetcher = sg.Column(
    [
        [
            sg.Text(
                "This program finds the most recent date for each subject "
                "selected from one or more date fields and compares that with "
                "today's date to indicate how long it has been since the "
                "subject's most recent visit.",
                size=(73, 3),
            )
        ],
        [sg.Text("1. REDCap Project API Token "), sg.InputText(k="TOKEN")],
        [fetch_status, fetch_button],
    ]
)

MULTI = sg.LISTBOX_SELECT_MODE_MULTIPLE
filter_input = sg.Column(
    [
        [sg.Text("2. Choose one or more fields to find the most recent date from:")],
        [
            sg.Listbox(values=[], k="FIELDS", pad=(0, 0), s=(30, 6), select_mode=MULTI),
            sg.Button("2. Filter Records", k="FILTER_BUTTON"),
        ],
    ],
)

filter_error = sg.pin(sg.Text("", s=(0, 1), k="FILTER_ERROR"))

TABLE_HEADER = ["Subject", "Date Last Seen", "Days Ago"]
filter_output = sg.pin(
    sg.Column(
        [
            [sg.Text("", s=(0, 1), k="FILTER_MSG")],
            [
                sg.Input(key="SAVE_LOCATION", visible=False, enable_events=True),
                sg.FolderBrowse(
                    button_text="Save this table as 'Report.xlsx'",
                    initial_folder=str(Path.home()),
                    auto_size_button=True,
                    target="SAVE_LOCATION",
                    k="SAVE_BUTTON",
                ),
            ],
            [sg.Text("", s=(0, 1), k="SAVE_MESSAGE", visible=False)],
            [
                sg.pin(
                    sg.Table(
                        [["" for _ in range(len(TABLE_HEADER))]],
                        headings=["Row"] + TABLE_HEADER,
                        auto_size_columns=False,
                        k="DATA",
                        font=table_font,
                    )
                )
            ],
        ],
        k="FILTER_OUTPUT",
        pad=(0, 0),
    )
)
filter_result = sg.pin(
    sg.Column([[filter_error, filter_output]], k="FILTER_RESULT", pad=(0, 0))
)
filterer = sg.pin(
    sg.Column(
        [[filter_input], [filter_result]], k="FILTERER", pad=(0, 0), visible=False
    )
)


layout = [
    [fetcher],
    [filterer],
]

# Create the Window
window = sg.Window("REDCap Patient Last Seen Report", layout, finalize=True)
window["FETCH_BAR"].Widget.config(mode="indeterminate")

# REDCap fetch thread body
def fetch_redcap_data():
    try:
        r = REDCapStudy("https://redcap.chop.edu/api/", values["TOKEN"])
        date_fields = sorted(
            f["field_name"]
            for f in r.get_data_dictionary()
            if "date" in f["text_validation_type_or_show_slider_number"]
        )
        records = r.get_records(fields=date_fields)
    except Exception as e:
        raise Exception(
            "REDCap Error: " + json.loads(re.search("({.*})", str(e))[1])["error"]
        )
    return date_fields, records


tpex = ThreadPoolExecutor(max_workers=1)


def fetch_completed(future):
    try:
        global date_fields, records
        date_fields, records = future.result()
        window["FIELDS"].update(values=date_fields)
        window["FILTER_RESULT"].update(visible=False)
        window["FILTERER"].update(visible=True)
    except Exception as e:
        window["FETCH_ERROR"].update(str(e), visible=True)
    finally:
        window["FETCH_BAR"].update(window["FETCH_BAR"].Widget["value"], visible=False)
        window["FETCH_BUTTON"].update(visible=True)


def filter_records(records, chosen_fields):
    values = {}
    for rec in records:
        if rec["field_name"] in chosen_fields:
            values.setdefault(rec["record"], set()).add(rec["value"])
    return {k: sorted(v)[-1] for k, v in values.items()}


def table_to_widget(table, table_widget):
    data = [
        [i + 1] + [" " + str(v) + " " for v in r.values()] for i, r in enumerate(table)
    ]
    char_width = sg.Text.char_width_in_pixels(table_font)
    col_widths = {c: len(c) for c in ["Row"] + TABLE_HEADER}
    for r in table:
        for k, v in r.items():
            col_widths[k] = max(col_widths.get(k), len(str(v)))
    row_colors = []
    for i, r in enumerate(table):
        v = r["Days Ago"]
        if v < 0:
            row_colors.append((i, "black", "#FFDDDD"))
        elif v > 365:
            row_colors.append((i, "black", "#D2EFFF"))

    table_widget.update(values=data, num_rows=min(25, len(data)), row_colors=row_colors)
    table_widget.Widget.pack_forget()
    for cid, width in col_widths.items():
        table_widget.Widget.column(cid, width=(width + 2) * char_width)
    table_widget.Widget.pack(side="left", fill="both", expand=True)
    table_widget.expand(True, True, True)


def table_to_excel(table, source_fields, filepath):
    workbook = xlsxwriter.Workbook(filepath)
    worksheet = workbook.add_worksheet()

    col_widths = {c: len(c) for c in TABLE_HEADER}
    for r in table:
        for k, v in r.items():
            col_widths[k] = max(col_widths.get(k), len(str(v)))

    for i, width in enumerate([col_widths[c] for c in TABLE_HEADER]):
        worksheet.set_column(i, i, width)

    header = workbook.add_format({"bold": True, "border": 1})
    red = workbook.add_format({"bg_color": "#FFDDDD"})
    blue = workbook.add_format({"bg_color": "#D2EFFF"})
    worksheet.write(0, 0, f"Source Fields: {', '.join(source_fields)}", header)
    worksheet.write_row(2, 0, TABLE_HEADER, header)
    for i, r in enumerate(table):
        if r["Days Ago"] < 0:
            fmt = red
        elif r["Days Ago"] > 365:
            fmt = blue
        else:
            fmt = None
        worksheet.write_row(i + 3, 0, [r[c] for c in TABLE_HEADER], fmt)

    workbook.close()


# Main event loop
event, values = None, None
refresh_future = None
while True:
    prev_event, prev_values = event, values
    window["SAVE_LOCATION"].update("")
    event, values = window.read(timeout=100)
    if (event != prev_event) or (values != prev_values):
        if event == sg.WIN_CLOSED:
            break
        elif event == "FETCH_BUTTON":
            date_fields, records = None, None
            window["FILTERER"].update(visible=False)
            window["FETCH_BUTTON"].update(visible=False)
            window["FETCH_ERROR"].update("", visible=False)
            window["FETCH_BAR"].update(
                window["FETCH_BAR"].Widget["value"], visible=True
            )
            refresh_future = tpex.submit(fetch_redcap_data)
        elif event == "FILTER_BUTTON":
            chosen_fields = values["FIELDS"]
            window["FILTER_RESULT"].update(visible=True)
            if not chosen_fields:
                window["FILTER_OUTPUT"].update(visible=False)
                window["FILTER_ERROR"].set_size((0, 1))
                window["FILTER_ERROR"].update(
                    "Error: Please choose one or more date fields.", visible=True
                )
                continue

            dates = filter_records(records, chosen_fields)
            if not dates:
                continue

            today = arrow.now()
            table = []
            for i in sorted(dates.items(), key=lambda i: i[1]):
                then = arrow.get(i[1])
                days_ago = (today - then).days
                table.append(dict(zip(TABLE_HEADER, [i[0], i[1], days_ago])))

            table = sorted(
                table,
                key=lambda r: r["Days Ago"] - 99999
                if (r["Days Ago"] < 0)
                else -r["Days Ago"],
            )

            msg = f"Using chosen fields:"
            year_sum = sum(r["Days Ago"] > 365 for r in table)
            future_sum = sum(r["Days Ago"] < 0 for r in table)
            msg += f"  \nLast seen more than a year ago:\t{year_sum}"
            if future_sum > 0:
                msg += f"  \nLast seen IN THE FUTURE???:\t{future_sum}"

            table_to_widget(table, window["DATA"])
            window["FILTER_MSG"].set_size((None, len(msg.split("\n"))))
            window["FILTER_MSG"].update(msg)
            window["FILTER_ERROR"].update(visible=False)
            window["SAVE_MESSAGE"].update(visible=False)
            window["FILTER_OUTPUT"].update(visible=True)
        elif event == "SAVE_LOCATION":
            if values["SAVE_LOCATION"]:
                try:
                    table_to_excel(
                        table, chosen_fields, values["SAVE_LOCATION"] + "/Report.xlsx"
                    )
                except Exception as e:
                    window["SAVE_MESSAGE"].update(f"Error: {str(e)}", visible=True)
                else:
                    window["SAVE_MESSAGE"].update(
                        f'Saved {values["SAVE_LOCATION"] + "/Report.xlsx"}',
                        visible=True,
                    )
            else:
                window["SAVE_MESSAGE"].update(visible=False)

    if refresh_future and refresh_future.done():
        fetch_completed(refresh_future)
        refresh_future = None

    if window["FETCH_BAR"].visible:
        window["FETCH_BAR"].Widget["value"] += 1
