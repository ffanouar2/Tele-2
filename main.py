import os
import io
import gzip
import marshal
import asyncio
import threading
import subprocess
from pathlib import Path

import telebot
from telebot import types
from flask import Flask


# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.environ["BOT_TOKEN"]

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

app = Flask(__name__)


# ============================================================
# RENDER WEB SERVER
# ============================================================

@app.route("/")
def home():
    return "ANOUAR Code Packer is running.", 200


@app.route("/health")
def health():
    return "OK", 200


def run_web():
    port = int(os.environ.get("PORT", "10000"))
    app.run(
        host="0.0.0.0",
        port=port,
        threaded=True
    )


# ============================================================
# BYTE HELPERS
# ============================================================

def xbytes(data: bytes) -> str:
    """
    Converts every byte to:
        \\xNN
    """
    return "".join(f"\\x{b:02x}" for b in data)


def python_bytes(data: bytes) -> str:
    """
    Python-style bytes literal.
    Example:
        b'\\x1f\\x8b\\x08...'
    """
    return repr(data)


def gzip_data(data: bytes) -> bytes:
    return gzip.compress(
        data,
        compresslevel=9,
        mtime=0
    )


def filename_without_extension(filename):
    return Path(filename).stem


# ============================================================
# PYTHON
# ============================================================

def pack_python(source: bytes, filename: str) -> bytes:
    """
    Python:
        source
          ↓
        compile
          ↓
        marshal
          ↓
        gzip
          ↓
        b'\\x1f\\x8b...'
    """

    text = source.decode("utf-8")

    code = compile(
        text,
        filename,
        "exec"
    )

    marshalled = marshal.dumps(code)

    compressed = gzip_data(marshalled)

    payload = python_bytes(compressed)

    output = f'''import marshal
import gzip

exec(marshal.loads(gzip.decompress({payload})))
'''

    return output.encode("utf-8")


# ============================================================
# JAVASCRIPT
# ============================================================

def pack_javascript(source: bytes, filename: str) -> bytes:

    compressed = gzip_data(source)
    payload = xbytes(compressed)

    output = f'''// ANOUAR PACKED JAVASCRIPT
// Original: {filename}

const __packed = "{payload}";

const __bytes = Uint8Array.from(
    __packed,
    c => c.charCodeAt(0)
);

const __source = require("zlib")
    .gunzipSync(Buffer.from(__bytes))
    .toString("utf8");

eval(__source);
'''

    return output.encode()


# ============================================================
# TYPESCRIPT
# ============================================================

def pack_typescript(source: bytes, filename: str) -> bytes:

    compressed = gzip_data(source)
    payload = xbytes(compressed)

    output = f'''// ANOUAR PACKED TYPESCRIPT
// Original: {filename}

const __packed: string = "{payload}";

const __bytes = Uint8Array.from(
    __packed,
    c => c.charCodeAt(0)
);

import {{ gunzipSync }} from "zlib";

const __source = gunzipSync(
    Buffer.from(__bytes)
).toString("utf8");

eval(__source);
'''

    return output.encode()


# ============================================================
# HTML
# ============================================================

def pack_html(source: bytes, filename: str) -> bytes:

    compressed = gzip_data(source)
    payload = xbytes(compressed)

    output = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>{filename}</title>
</head>

<body>

<script>
(async () => {{

    const __packed = "{payload}";

    const __bytes = Uint8Array.from(
        __packed,
        c => c.charCodeAt(0)
    );

    const __stream = new Blob([__bytes])
        .stream()
        .pipeThrough(
            new DecompressionStream("gzip")
        );

    const __source =
        await new Response(__stream).text();

    document.open();
    document.write(__source);
    document.close();

}})();
</script>

</body>
</html>
'''

    return output.encode()


# ============================================================
# PHP
# ============================================================

def pack_php(source: bytes, filename: str) -> bytes:

    compressed = gzip_data(source)
    payload = xbytes(compressed)

    output = f'''<?php

// ANOUAR PACKED PHP
// Original: {filename}

$__packed = "{payload}";

$__source = gzdecode($__packed);

eval("?>" . $__source);

?>
'''

    return output.encode()


# ============================================================
# RUBY
# ============================================================

def pack_ruby(source: bytes, filename: str) -> bytes:

    compressed = gzip_data(source)
    payload = xbytes(compressed)

    output = f'''require "zlib"
require "stringio"

# ANOUAR PACKED RUBY
# Original: {filename}

__packed = "{payload}"

__source = Zlib::GzipReader
    .new(StringIO.new(__packed))
    .read

eval(
    __source,
    TOPLEVEL_BINDING,
    "{filename}",
    1
)
'''

    return output.encode()


# ============================================================
# BASH
# ============================================================

def pack_bash(source: bytes, filename: str) -> bytes:

    compressed = gzip_data(source)
    payload = xbytes(compressed)

    output = f'''#!/usr/bin/env bash

# ANOUAR PACKED BASH
# Original: {filename}

printf '%b' '{payload}' | gzip -d | bash
'''

    return output.encode()


# ============================================================
# LUA
# ============================================================

def pack_lua(source: bytes, filename: str) -> bytes:

    compressed = gzip_data(source)
    payload = xbytes(compressed)

    output = f'''-- ANOUAR PACKED LUA
-- Original: {filename}
-- Requires a Lua gzip/zlib library.

local packed = "{payload}"

local zlib = require("zlib")

local source = zlib.inflateGzip(packed)

assert(
    load(source, "{filename}")
)()
'''

    return output.encode()


# ============================================================
# C
# ============================================================

def pack_c(source: bytes, filename: str) -> bytes:

    compressed = gzip_data(source)

    array = ",".join(
        f"0x{b:02x}"
        for b in compressed
    )

    output = f'''/*
 ANOUAR PACKED C
 Original: {filename}

 This stores the compressed source as a byte array.
 A gzip decompression implementation/library is required
 to execute the recovered source.
*/

#include <stddef.h>

static const unsigned char packed_data[] = {{
    {array}
}};

static const size_t packed_size =
    sizeof(packed_data);
'''

    return output.encode()


# ============================================================
# C++
# ============================================================

def pack_cpp(source: bytes, filename: str) -> bytes:

    compressed = gzip_data(source)

    array = ",".join(
        f"0x{b:02x}"
        for b in compressed
    )

    output = f'''/*
 ANOUAR PACKED C++
 Original: {filename}

 Compressed source bytes.
*/

#include <cstddef>

static const unsigned char packed_data[] = {{
    {array}
}};

static const std::size_t packed_size =
    sizeof(packed_data);
'''

    return output.encode()


# ============================================================
# JAVA
# ============================================================

def pack_java(source: bytes, filename: str) -> bytes:

    compressed = gzip_data(source)

    array = ",".join(
        f"(byte)0x{b:02x}"
        for b in compressed
    )

    classname = filename_without_extension(filename)
    classname = "".join(
        c if c.isalnum() else "_"
        for c in classname
    )

    output = f'''import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.zip.GZIPInputStream;

public class {classname} {{

    static final byte[] PACKED = new byte[] {{
        {array}
    }};

    public static void main(String[] args)
            throws Exception {{

        ByteArrayInputStream input =
            new ByteArrayInputStream(PACKED);

        GZIPInputStream gzip =
            new GZIPInputStream(input);

        ByteArrayOutputStream out =
            new ByteArrayOutputStream();

        byte[] buffer = new byte[8192];

        int n;

        while ((n = gzip.read(buffer)) != -1) {{
            out.write(buffer, 0, n);
        }}

        String source =
            out.toString(StandardCharsets.UTF_8);

        System.out.println(source);
    }}
}}
'''

    return output.encode()


# ============================================================
# C#
# ============================================================

def pack_csharp(source: bytes, filename: str) -> bytes:

    compressed = gzip_data(source)

    array = ",".join(
        f"0x{b:02X}"
        for b in compressed
    )

    output = f'''using System;
using System.IO;
using System.IO.Compression;
using System.Text;

class Program
{{
    static byte[] packed = new byte[]
    {{
        {array}
    }};

    static void Main()
    {{
        using var input =
            new MemoryStream(packed);

        using var gzip =
            new GZipStream(
                input,
                CompressionMode.Decompress
            );

        using var output =
            new MemoryStream();

        gzip.CopyTo(output);

        string source =
            Encoding.UTF8.GetString(
                output.ToArray()
            );

        Console.WriteLine(source);
    }}
}}
'''

    return output.encode()


# ============================================================
# GO
# ============================================================

def pack_go(source: bytes, filename: str) -> bytes:

    compressed = gzip_data(source)

    array = ",".join(
        f"0x{b:02x}"
        for b in compressed
    )

    output = f'''package main

import (
    "bytes"
    "compress/gzip"
    "io"
    "fmt"
)

var packed = []byte{{
    {array}
}}

func main() {{

    reader, err :=
        gzip.NewReader(
            bytes.NewReader(packed)
        )

    if err != nil {{
        panic(err)
    }}

    data, err :=
        io.ReadAll(reader)

    if err != nil {{
        panic(err)
    }}

    fmt.Print(string(data))
}}
'''

    return output.encode()


# ============================================================
# RUST
# ============================================================

def pack_rust(source: bytes, filename: str) -> bytes:

    compressed = gzip_data(source)

    array = ",".join(
        f"0x{b:02x}"
        for b in compressed
    )

    output = f'''// ANOUAR PACKED RUST
// Original: {filename}
//
// Requires a gzip crate such as flate2.

static PACKED: &[u8] = &[
    {array}
];

fn main() {{

    println!("Packed source size: {{}} bytes",
        PACKED.len());

}}
'''

    return output.encode()


# ============================================================
# KOTLIN
# ============================================================

def pack_kotlin(source: bytes, filename: str) -> bytes:

    compressed = gzip_data(source)

    array = ",".join(
        f"0x{b:02X}"
        for b in compressed
    )

    output = f'''import java.io.ByteArrayInputStream
import java.util.zip.GZIPInputStream

fun main() {{

    val packed = byteArrayOf(
        {array}
    )

    val gzip =
        GZIPInputStream(
            ByteArrayInputStream(packed)
        )

    val source =
        gzip.readBytes()
            .toString(Charsets.UTF_8)

    println(source)
}}
'''

    return output.encode()


# ============================================================
# SWIFT
# ============================================================

def pack_swift(source: bytes, filename: str) -> bytes:

    compressed = gzip_data(source)

    array = ",".join(
        f"0x{b:02X}"
        for b in compressed
    )

    output = f'''import Foundation

// ANOUAR PACKED SWIFT
// Original: {filename}

let packed: [UInt8] = [
    {array}
]

print("Packed bytes: \\(packed.count)")
'''

    return output.encode()


# ============================================================
# DART
# ============================================================

def pack_dart(source: bytes, filename: str) -> bytes:

    compressed = gzip_data(source)

    array = ",".join(
        f"0x{b:02x}"
        for b in compressed
    )

    output = f'''import 'dart:typed_data';

void main() {{

  final packed = Uint8List.fromList([
    {array}
  ]);

  print("Packed bytes: ${{packed.length}}");
}}
'''

    return output.encode()


# ============================================================
# CSS
# ============================================================

def pack_css(source: bytes, filename: str) -> bytes:

    compressed = gzip_data(source)
    payload = xbytes(compressed)

    output = f'''/*
ANOUAR PACKED CSS

Original: {filename}

Compressed bytes:
{payload}

CSS itself cannot execute a gzip
decompression loader. The bytes are
stored inside this CSS file.
*/
'''

    return output.encode()


# ============================================================
# JSON
# ============================================================

def pack_json(source: bytes, filename: str) -> bytes:

    compressed = gzip_data(source)
    payload = xbytes(compressed)

    output = f'''{{
  "packer": "ANOUAR",
  "original": "{filename}",
  "compression": "gzip",
  "encoding": "escaped-bytes",
  "data": "{payload}"
}}
'''

    return output.encode()


# ============================================================
# XML
# ============================================================

def pack_xml(source: bytes, filename: str) -> bytes:

    compressed = gzip_data(source)
    payload = xbytes(compressed)

    output = f'''<?xml version="1.0" encoding="UTF-8"?>
<anouar-packed
    original="{filename}"
    compression="gzip"
    encoding="escaped-bytes">
    <data>{payload}</data>
</anouar-packed>
'''

    return output.encode()


# ============================================================
# YAML
# ============================================================

def pack_yaml(source: bytes, filename: str) -> bytes:

    compressed = gzip_data(source)
    payload = xbytes(compressed)

    output = f'''packer: ANOUAR
original: "{filename}"
compression: gzip
encoding: escaped-bytes
data: "{payload}"
'''

    return output.encode()


# ============================================================
# SQL
# ============================================================

def pack_sql(source: bytes, filename: str) -> bytes:

    compressed = gzip_data(source)
    payload = xbytes(compressed)

    output = f'''/*
ANOUAR PACKED SQL
Original: {filename}

Compressed bytes:
{payload}

SQL has no universal built-in gzip
source-loader, so this is stored as
packed bytes.
*/
'''

    return output.encode()


# ============================================================
# EXTENSION MAP
# ============================================================

PACKERS = {

    ".py": pack_python,

    ".js": pack_javascript,
    ".mjs": pack_javascript,
    ".cjs": pack_javascript,

    ".ts": pack_typescript,
    ".tsx": pack_typescript,

    ".html": pack_html,
    ".htm": pack_html,

    ".php": pack_php,

    ".rb": pack_ruby,

    ".sh": pack_bash,
    ".bash": pack_bash,

    ".lua": pack_lua,

    ".c": pack_c,
    ".h": pack_c,

    ".cpp": pack_cpp,
    ".cc": pack_cpp,
    ".cxx": pack_cpp,
    ".hpp": pack_cpp,

    ".java": pack_java,

    ".cs": pack_csharp,

    ".go": pack_go,

    ".rs": pack_rust,

    ".kt": pack_kotlin,
    ".kts": pack_kotlin,

    ".swift": pack_swift,

    ".dart": pack_dart,

    ".css": pack_css,

    ".json": pack_json,

    ".xml": pack_xml,

    ".yaml": pack_yaml,
    ".yml": pack_yaml,

    ".sql": pack_sql,
}


# ============================================================
# PACK FUNCTION
# ============================================================

def pack_file(filename: str, source: bytes):

    extension = Path(filename).suffix.lower()

    packer = PACKERS.get(extension)

    if packer is None:
        raise ValueError(
            f"Deze extensie wordt niet ondersteund: {extension}"
        )

    return packer(source, filename)


# ============================================================
# TELEGRAM COMMANDS
# ============================================================

@bot.message_handler(commands=["start"])
def start(message):

    text = """
<b>ANOUAR CODE PACKER</b>

Stuur een ondersteund codebestand.

De bot maakt een packed versie met:
• gzip
• escaped binary bytes
• eigen loader per taal

Python gebruikt:
<code>marshal + gzip</code>

Voorbeeld:

<code>acc.py → acc.py</code>
<code>index.html → index.html</code>
<code>app.js → app.js</code>

Gebruik /languages om alle ondersteunde talen
te bekijken.
"""

    bot.reply_to(message, text)


@bot.message_handler(commands=["languages"])
def languages(message):

    extensions = sorted(PACKERS.keys())

    text = "<b>ONDERSTEUNDE EXTENSIES</b>\n\n"

    text += " ".join(
        f"<code>{x}</code>"
        for x in extensions
    )

    bot.reply_to(message, text)


# ============================================================
# DOCUMENT HANDLER
# ============================================================

@bot.message_handler(content_types=["document"])
def document_handler(message):

    document = message.document

    filename = document.file_name or "file"

    extension = Path(filename).suffix.lower()

    if extension not in PACKERS:

        bot.reply_to(
            message,
            f"❌ Extensie <code>{extension}</code> wordt "
            f"nog niet ondersteund.\n\n"
            f"Gebruik /languages."
        )

        return

    status = bot.reply_to(
        message,
        f"⏳ <b>PACKING</b>\n"
        f"<code>{filename}</code>"
    )

    try:

        file_info = bot.get_file(
            document.file_id
        )

        source = bot.download_file(
            file_info.file_path
        )

        packed = pack_file(
            filename,
            source
        )

        output_name = filename

        bot.delete_message(
            message.chat.id,
            status.message_id
        )

        bot.send_document(
            message.chat.id,
            io.BytesIO(packed),
            visible_file_name=output_name,
            caption=(
                f"✅ <b>Packed</b>\n\n"
                f"📄 <code>{filename}</code>\n"
                f"📦 gzip + escaped bytes\n"
                f"🔧 eigen loader\n"
                f"📁 extensie behouden"
            )
        )

    except Exception as e:

        try:
            bot.delete_message(
                message.chat.id,
                status.message_id
            )
        except Exception:
            pass

        bot.reply_to(
            message,
            "❌ <b>Fout tijdens packen</b>\n\n"
            f"<code>{str(e)[:3000]}</code>"
        )


# ============================================================
# ERROR HANDLING
# ============================================================

@bot.message_handler(
    func=lambda message: True,
    content_types=["text"]
)
def text_handler(message):

    if message.text.startswith("/"):
        return

    bot.reply_to(
        message,
        "📁 Stuur een codebestand als document.\n\n"
        "Gebruik /languages voor de ondersteunde talen."
    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    web_thread = threading.Thread(
        target=run_web,
        daemon=True
    )

    web_thread.start()

    print("ANOUAR Code Packer started.")

    bot.infinity_polling(
        skip_pending=True,
        timeout=30,
        long_polling_timeout=30
    )   