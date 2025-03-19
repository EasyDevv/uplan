import gradio as gr

with gr.Blocks() as demo:
    gr.Markdown("Welcome to the Gradio App!")
    gr.Button("Click")

demo.launch()
