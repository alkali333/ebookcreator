import os
import streamlit as st
import pdfkit
import ollama

# Define the Ollama model to use
OLLAMA_MODEL = "dolphinllama"  # Change this to your preferred model

def create_chapters(number: int, title: str, description: str) -> list:
    """Create a list of chapters for the ebook"""
    prompt = f"""Create a list of {number} chapters for an ebook, include introductory 
    and concluding chapters and create interesting names for the introduction and 
    conclusion chapter. Respond only with the chapter names separated by commas.
    Don't include the number or the word 'chapter'.
    The book has the following title and description:
    Book Title: {title}, Book Description: {description or "not supplied"}"""
    
    response = ollama.generate(
        model=OLLAMA_MODEL,
        prompt=prompt
    )
    
    content = response['response']
    content = content.replace("\n", " ")
    chapters = content.split(",")
    return [chapter.strip() for chapter in chapters][:number]

def write_next_chapter(
    book_name: str,
    book_description: str,
    chapter_number: int,
    chapter_name: str,
    summary_so_far: str,
    number_of_words: int = 350,
) -> str:
    """Writes the next chapter continuing from summary so far"""

    if chapter_number == 1:
        prompt = f"""You are writing the first chapter of an ebook. Make this first chapter interesting to 
        encourage the user to read on. Write approximately {number_of_words} words.
        
        BOOK NAME: {book_name}
        BOOK DESCRIPTION: {book_description or "not supplied"}
        CHAPTER NUMBER: {chapter_number}
        CHAPTER NAME: {chapter_name}
        """
    else:
        prompt = f"""You are writing a chapter of an ebook. Write approximately {number_of_words} words.
        Use the previous chapter summaries provided to keep a consistent narrative. Make this
        chapter follow naturally from the previous chapter ({chapter_number - 1}) provided 
        in the summary below.
        Don't mention the present or previous chapters by name.
        
        BOOK NAME: {book_name}
        BOOK DESCRIPTION: {book_description or "not supplied"}
        SUMMARY SO FAR: {summary_so_far}
        CHAPTER NUMBER: {chapter_number}
        CHAPTER NAME: {chapter_name}
        """

    response = ollama.generate(
        model=OLLAMA_MODEL,
        prompt=prompt
    )
    
    return response['response']

def summarize(input: str, number_of_words: int) -> str:
    """Summarizes the chapter, including list of key themes and ideas"""
    prompt = f"""You are writing a {number_of_words} word summary of an ebook chapter:
    
    Book Chapter: {input}
    """
    
    response = ollama.generate(
        model=OLLAMA_MODEL,
        prompt=prompt
    )
    
    return response['response']

# Streamlit app
st.title("Create An Ebook with Ollama")
st.caption(f"Using local model: {OLLAMA_MODEL}")
input_title = st.text_input("Book Title")
input_description = st.text_input("Book Description")
input_number = st.selectbox("Number Of Chapters", list(range(1, 21)), index=6)
input_words = st.number_input("Words Per Chapter", value=350, step=1)
submit_button = st.button("Submit")

if submit_button and input_title:
    chapter_list = []
    ebook_content = ""
    summary_so_far = ""

    with st.spinner("Creating chapter list..."):
        try:
            chapter_list = create_chapters(
                number=input_number,
                title=input_title,
                description=input_description,
            )
            
            # Display chapters
            st.subheader("Chapters:")
            for field in chapter_list:
                st.write(field.strip())
                
        except Exception as e:
            st.error(f"An error occurred: {e}")
            raise

    for i, chapter in enumerate(chapter_list):
        ebook_content += f"<h1>Chapter {i+1}: {chapter}</h1> \n\n"

        with st.spinner(f"Writing Chapter {i+1}..."):
            try:
                response = write_next_chapter(
                    book_name=input_title,
                    book_description=input_description,
                    chapter_number=i + 1,
                    chapter_name=chapter,
                    summary_so_far=summary_so_far,
                    number_of_words=input_words,
                )
            except Exception as e:
                st.error(f"An error occurred while writing chapter {i+1}: {e}")
                raise

            st.subheader(f"CHAPTER {i+1}: {chapter}")
            st.write(response)
            ebook_content += "<p>" + response.replace("\n", "</p><p>") + "</p><br/><br/><br/>"

        with st.spinner(f"Thinking about chapter {i+1}..."):
            # summary length is a fraction of the number of words, but must be between 50 and 150
            summary_length = max(min(round(input_words / 7), 100), 50)
            try:
                summary = summarize(input=response, number_of_words=summary_length)
            except Exception as e:
                st.error(f"An error occurred summarizing chapter: {e}")
                raise

            if len(summary_so_far.split()) > 1200:
                st.write("Summary exceeds 1000 words, reducing...")
                with st.spinner("Reviewing the story so far... "):
                    try:
                        summary_so_far = summarize(
                            input=summary_so_far, number_of_words=600
                        )
                    except Exception as e:
                        st.error(
                            f"An error occurred while summarizing the story so far: {e}"
                        )
                        raise

            # We always want the most recent chapter in full
            summary_so_far += f"Chapter {i+1} Summary: {summary} \n\n"

            st.subheader(f"CHAPTER {i + 1} Summary")
            st.write(summary)

    # Generate PDF
    file_name = f'{input_title.strip().replace(" ", "_")}.pdf'
    
    # Create ebooks directory if it doesn't exist
    os.makedirs("ebooks", exist_ok=True)
    file_path = os.path.join("ebooks", file_name)

    try:
        pdfkit.from_string(ebook_content, file_path, options={"encoding": "UTF-8"})
    except Exception as e:
        st.error(f"An error occurred while creating the PDF: {e}")
        raise

    st.success("Ebook content written to file successfully!")

    try:
        with open(file_path, "rb") as f:
            data = f.read()
    except Exception as e:
        st.error(f"An error occurred while reading the file: {e}")
        raise

    st.download_button("Download Ebook", data, file_name, "application/pdf")